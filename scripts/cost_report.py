"""Cost report from logged runs: tokens and Rs per real user session (median, P90), by stage, and 10,000-user projections.
Usage (server): GET /api/admin/cost_report?fixed_infra_inr=0   Local: python -m scripts.cost_report"""
import statistics
from datetime import date
from claimcheck import config, db

USER_STAGES = {"extract", "reason", "generate", "embed_query"}


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else 0


def build(fixed_infra_inr: float = 0.0) -> str:
    rows = db.rest("GET", "runs", params={"select": "session_id,stage,model,pipeline_version,prompt_tokens,output_tokens,"
                                                    "thoughts_tokens,cached_tokens,tool_prompt_tokens,cost_inr,latency_ms,ok",
                                          "pipeline_version": "eq.v3", "order": "id.desc", "limit": "20000"}) or []
    sessions = {}
    for r in rows:
        if r["stage"] in USER_STAGES:
            sessions.setdefault(r["session_id"], []).append(r)
    sessions = {k: v for k, v in sessions.items() if any(x["stage"] == "extract" for x in v) and any(x["stage"] == "reason" for x in v)}
    if not sessions:
        return "# Cost report\n\nNo complete live sessions logged yet (a session = extract + reason)."
    tok = lambda x: (x["prompt_tokens"] or 0) + (x["output_tokens"] or 0) + (x["thoughts_tokens"] or 0) + (x["tool_prompt_tokens"] or 0)
    cost = [sum(float(x["cost_inr"] or 0) for x in v) for v in sessions.values()]
    toks = [sum(tok(x) for x in v) for v in sessions.values()]
    calls = [len(v) for v in sessions.values()]
    by_stage = {}
    for v in sessions.values():
        per = {}
        for x in v:
            s = per.setdefault(x["stage"], [0, 0.0, 0, 0, 0])
            s[0] += tok(x); s[1] += float(x["cost_inr"] or 0); s[2] += x["prompt_tokens"] or 0; s[3] += (x["output_tokens"] or 0) + (x["thoughts_tokens"] or 0); s[4] += 1
        for st, s in per.items():
            by_stage.setdefault(st, []).append(s)
    med_c, p90_c = statistics.median(cost), _pct(cost, .9)
    out = ["# ClaimCheck cost report", "", f"Generated {date.today()} from {len(sessions)} logged live sessions (pipeline v3). "
           f"Prices: {', '.join(f'{m} ${p[1]}/${p[2]} per 1M in/out' for m, p in ((m, config.price(m)) for m in sorted(set(config.MODELS.values()))))}; USD/INR {config.USD_INR}.", "",
           "## One session (upload documents -> checks -> estimate -> explanations)", "",
           "| Metric | Median | P90 |", "|---|---|---|",
           f"| Tokens per session | {statistics.median(toks):,.0f} | {_pct(toks, .9):,.0f} |",
           f"| Rs per session | {med_c:.2f} | {p90_c:.2f} |", f"| LLM/embedding calls per session | {statistics.median(calls):.0f} | {_pct(calls, .9):.0f} |", "",
           "| Stage | Median tokens | Median input | Median output+thinking | Median calls | Median Rs |", "|---|---|---|---|---|---|"]
    for st, ss in sorted(by_stage.items()):
        out.append(f"| {st} | {statistics.median(s[0] for s in ss):,.0f} | {statistics.median(s[2] for s in ss):,.0f} | "
                   f"{statistics.median(s[3] for s in ss):,.0f} | {statistics.median(s[4] for s in ss):.0f} | {statistics.median(s[1] for s in ss):.3f} |")
    out += ["", "What-if slider and pack assembly make no LLM call (Rs 0). The cover letter / grievance letter adds one small generate call when used.", "",
            "## 10,000 users per month", "", "| Sessions per user per month | Sessions | Median Rs | P90 Rs | + fixed infra |", "|---|---|---|---|---|"]
    for s in (0.2, 1, 3):
        n = 10000 * s
        out.append(f"| {s} | {n:,.0f} | {n * med_c:,.0f} | {n * p90_c:,.0f} | {n * med_c + fixed_infra_inr:,.0f} |")
    out += ["", "Prices on 3.6 Flash rise on 1 Jan 2027 ($1.50/$7.50); Flash-Lite pricing is unchanged.", "",
            "## What we would change at scale", "",
            "1. Flash-Lite has no context caching: keep prompts small by retrieving only the top clauses (already done in v3).",
            "2. Cache the policy context only if a stage moves to Flash (cached input is 90% cheaper).",
            "3. Batch API (50% off) for evaluation reruns and re-embedding the corpus.",
            "4. Route only low-confidence (Review) items to the stronger model.",
            "5. Paid Gemini tier for rate-limit headroom; Supabase Pro and Vercel Pro for capacity; a human-review queue for Review items."]
    return "\n".join(out)


if __name__ == "__main__":
    print(build())
