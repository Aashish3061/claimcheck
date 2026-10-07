"""Evaluation harness: runs pipeline versions v0-v3 on synthetic cases with known ground truth, writes eval_runs,
and builds the report used on the evaluation slide. Runs server-side via /api/admin/eval_case (Gemini + Supabase).

v0  one call: all documents + full policy text -> the model estimates everything (= uploading to a general chatbot)
v1  separate extraction, then the model estimates from extracted items + full policy text (no engine)
v2  extraction + rule assignment from full policy text (no retrieval) + deterministic engine
v3  extraction + RAG function-calling agent + engine + verbatim evidence check + confidence gating (production)
"""
import json, os, statistics, time
from difflib import SequenceMatcher
from claimcheck import config, db, llm, reason
from claimcheck.rules import engine
from claimcheck.schemas import V0Estimate
from eval.wilson import wilson

ROOT = config.ROOT
CASES = json.load(open(os.path.join(ROOT, "eval", "cases.json")))
V0_SYSTEM = """You check an Indian health-insurance reimbursement claim. Using the policy text and the documents, estimate
how much the insurer will pay. Return each bill line with its amount and the payable amount, and the totals."""


def _pdfs(case_id):
    c = CASES[case_id]
    return [(n, open(os.path.join(ROOT, "sample_claims", case_id, f"{n}.pdf"), "rb").read()) for n in c["docs"]]


def _policy_text(policy_id, max_chars=120000):
    return "\n\n".join(f"[{r['chunk_id']} {r.get('section') or ''}] {r['content']}" for r in reason.gather_fulltext(policy_id, max_chars).values())


def _match(pred: list[dict], truth: list[dict]):
    """Greedy match predicted line items to truth by amount then description similarity."""
    used, pairs = set(), []
    for t in truth:
        best, bs = None, 0.0
        for k, p in enumerate(pred):
            if k in used:
                continue
            sc = (1.0 if p.get("amount") == t["amount"] else 0.0) + SequenceMatcher(None, p.get("description", "").lower(), t["description"].lower()).ratio()
            if sc > bs:
                best, bs = k, sc
        if best is not None and bs >= 0.9:
            used.add(best)
            pairs.append((t, pred[best]))
        else:
            pairs.append((t, None))
    return pairs


def _extract_all(case_id):
    from claimcheck.extract import extract_document
    return [(name, extract_document(data, "application/pdf")) for name, data in _pdfs(case_id)]


def _extraction_metrics(case, docs):
    ok = tot = 0
    for name, d in docs:
        tot += 1; ok += d["doc_type"] == name
        exp_name = case["doc_names"].get(name, case["patient"])
        if name != "tariff_card":
            tot += 1; ok += (d.get("patient_name") or "").strip().lower() == exp_name.lower()
            tot += 1; ok += d.get("discharge_date") == case["doc_dates"].get(name, case["discharge"])
    bill = next((d for n, d in docs if n == "final_bill"), {"line_items": []})
    for t, p in _match(bill["line_items"], case["items"]):
        tot += 2
        if p:
            ok += p["amount"] == t["amount"]
            ok += p["category"] == t["category"] or (t["category"] == "medical_practitioner_fees" and p["category"] == "medical_practitioner_fees")
    return ok, tot, bill["line_items"]


def run_case(case_id: str, version: str = "v3", model: str | None = None, thinking: str | None = None, split: str | None = None):
    saved = (dict(config.MODELS), dict(config.THINKING))
    try:
        return _run_case(case_id, version, model, thinking, split)
    finally:
        config.MODELS.clear(); config.MODELS.update(saved[0])
        config.THINKING.clear(); config.THINKING.update(saved[1])


def _run_case(case_id, version, model, thinking, split):
    case = CASES[case_id]
    exp = case["expected"]
    if model:
        for k in ("extract", "reason", "generate"):
            config.MODELS[k] = model
    if thinking:
        for k in ("extract", "reason", "generate", "v0"):
            config.THINKING[k] = thinking
    t0 = time.time()
    a = llm.acc()
    a["version"] = f"eval-{version}"
    m = dict(case_id=case_id, version=version)
    try:
        if version == "v0":
            parts = [llm.file_part(b, "application/pdf") for _, b in _pdfs(case_id)]
            r = llm.generate_json("v0", [llm.user(*parts, f"Policy: {case['policy_id']}. Sum insured Rs {case['sum_insured']}."
                                                 + (f" Eligible room rent Rs {case['eligible_room_rent_per_day']}/day." if case["eligible_room_rent_per_day"] else "")
                                                 + "\n\nPolicy text:\n" + _policy_text(case["policy_id"]))], V0Estimate, V0_SYSTEM)
            pred = [dict(description=i.description, amount=i.amount, payable=i.payable, flagged=i.payable < i.amount) for i in r.items]
            payable, at_risk = r.payable, r.at_risk
        else:
            docs = _extract_all(case_id)
            ok, tot, lines = _extraction_metrics(case, docs)
            m.update(extraction_correct=ok, extraction_total=tot)
            items = [dict(line_id=i["line_id"], description=i["description"], category=i["category"], amount=i["amount"],
                          room_days=i.get("room_days"), confirmed=False) for i in lines]
            if version == "v1":
                r = llm.generate_json("v0", [llm.user(f"Bill lines: {json.dumps(items)}\nSum insured Rs {case['sum_insured']}."
                                                     + (f" Eligible room rent Rs {case['eligible_room_rent_per_day']}/day." if case["eligible_room_rent_per_day"] else "")
                                                     + "\n\nPolicy text:\n" + _policy_text(case["policy_id"]))], V0Estimate, V0_SYSTEM)
                pred = [dict(description=i.description, amount=i.amount, payable=i.payable, flagged=i.payable < i.amount) for i in r.items]
                payable, at_risk = r.payable, r.at_risk
            else:
                rr = reason.assign_rules(case["policy_id"], items, "rag" if version == "v3" else "fulltext")
                # extraction is unconfirmed in eval; treat amounts as confirmed so gating reflects evidence only
                for i in items:
                    i["confirmed"] = True
                ev = rr["evidence"] if version == "v3" else {k: True for k in rr["evidence"]}
                est = engine.estimate_settlement(case["policy_id"], case["sum_insured"], items, rr["assignments"],
                                                 case["eligible_room_rent_per_day"], evidence=ev)
                pred = [dict(description=i["description"], amount=i["amount"], payable=i["payable"],
                             flagged=i["verdict"] == "AT_RISK", review=i["verdict"] == "REVIEW" and i["at_risk"] > 0) for i in est["items"]]
                payable, at_risk = est["payable"], est["at_risk"]
                quoted = [x for x in rr["assignments"] if x.get("policy_quote")]
                m.update(citations_total=len(quoted), citations_valid=sum(1 for x in quoted if rr["evidence_detail"][x["line_id"]]["policy_quote_verified"]))
        tp = fp = fn = rv = 0
        for t, p in _match(pred, exp["items"] and [dict(description=i["item"], amount=i["amount"], at_risk=i["at_risk"]) for i in exp["items"]]):
            truth_risk = t["at_risk"] > 0
            if p and p.get("flagged"):
                tp += truth_risk; fp += not truth_risk
            elif truth_risk:
                fn += 1
                rv += bool(p and p.get("review"))
        m.update(payable=payable, payable_true=exp["payable"], payable_abs_error=abs(payable - exp["payable"]),
                 at_risk=at_risk, at_risk_true=exp["at_risk"], tp=tp, fp=fp, fn=fn, review_of_fn=rv, ok=True)
    except Exception as e:
        m.update(ok=False, error=f"{type(e).__name__}: {str(e)[:200]}")
    m["unsupported_numbers"] = a.get("unsupported_numbers", 0)
    m["cost_inr"] = round(a["cost"], 4)
    m["latency_ms"] = int((time.time() - t0) * 1000)
    model_used = model or config.MODELS["extract"]
    try:
        db.insert("eval_runs", [dict(pipeline_version=version, model=model_used, thinking_level=thinking or config.THINKING["reason"],
                                     split=split or case["split"], case_id=case_id, metrics=m, cost_inr=m["cost_inr"], latency_ms=m["latency_ms"])])
    except Exception:
        pass
    return m


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else None


def build_report() -> str:
    rows = db.rest("GET", "eval_runs", params={"select": "*", "order": "id.asc", "limit": "2000"}) or []
    latest = {}
    for r in rows:  # keep the latest run per (version, model, thinking, case)
        latest[(r["pipeline_version"], r["model"], r["thinking_level"], r["case_id"])] = r
    groups = {}
    for (v, mdl, th, cid), r in latest.items():
        groups.setdefault((r["split"], v, mdl, th), []).append(r["metrics"])
    out = ["# ClaimCheck evaluation report", "",
           "Synthetic cases with known ground truth (fictional hospitals and patients; policy terms from public wordings). "
           "Precision/recall are per bill line; CI = Wilson 95%.", "",
           "| Split | Version | Model | Thinking | Cases | Extraction acc. | At-risk precision (95% CI) | Recall (flag) | Recall incl. Review | Median payable error (Rs) | Citation validity | Unsupported numbers | Rs/case median (P90) | Latency s median (P90) |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    fails = []
    for (sp, v, mdl, th), ms in sorted(groups.items()):
        good = [m for m in ms if m.get("ok")]
        tp, fp, fn, rv = (sum(m.get(k, 0) for m in good) for k in ("tp", "fp", "fn", "review_of_fn"))
        ec, et = sum(m.get("extraction_correct", 0) for m in good), sum(m.get("extraction_total", 0) for m in good)
        cv, ct = sum(m.get("citations_valid", 0) for m in good), sum(m.get("citations_total", 0) for m in good)
        lo, hi = wilson(tp, tp + fp)
        prec = f"{tp}/{tp + fp} = {tp / (tp + fp):.0%} ({lo:.0%}-{hi:.0%})" if tp + fp else "n/a"
        rec = f"{tp}/{tp + fn} = {tp / (tp + fn):.0%}" if tp + fn else "n/a"
        rec2 = f"{(tp + rv) / (tp + fn):.0%}" if tp + fn else "n/a"
        err = statistics.median([m["payable_abs_error"] for m in good]) if good else None
        costs, lats = [m["cost_inr"] for m in ms], [m["latency_ms"] / 1000 for m in ms]
        out.append(f"| {sp} | {v} | {mdl} | {th} | {len(ms)} ({len(ms) - len(good)} failed) | {f'{ec}/{et} = {ec / et:.0%}' if et else 'n/a'} | {prec} | {rec} | {rec2} | "
                   f"{err if err is not None else 'n/a'} | {f'{cv}/{ct} = {cv / ct:.0%}' if ct else 'n/a'} | {sum(m.get('unsupported_numbers', 0) for m in ms)} | "
                   f"{statistics.median(costs):.2f} ({_pct(costs, .9):.2f}) | {statistics.median(lats):.1f} ({_pct(lats, .9):.1f}) |")
        for m in ms:
            if not m.get("ok"):
                fails.append(f"- {sp}/{v}/{mdl}: {m['case_id']} errored: {m.get('error')}")
            elif m.get("fp") or m.get("fn") or m.get("payable_abs_error"):
                fails.append(f"- {sp}/{v}/{mdl}: {m['case_id']} payable error Rs {m['payable_abs_error']:,}, FP {m.get('fp')}, FN {m.get('fn')}")
    out += ["", "## What failed", ""] + (fails or ["- nothing in these runs"])
    out += ["", "Award cases from Ombudsman compilations are not yet included: none are verified (see docs/human_checks.md)."]
    return "\n".join(out)
