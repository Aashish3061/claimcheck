"""Stage 6: plain-English explanations and letters. Inputs are the findings JSON only; a number guard rejects any
number not present in the input, with a deterministic template fallback. Nothing is ever sent automatically."""
import json
from claimcheck import evidence, llm
from claimcheck.rules.engine import profile
from claimcheck.schemas import Explanations, Letter

STYLE = """Write in plain English for an Indian policyholder. Use ONLY facts and numbers present in the input JSON;
do not introduce any new number, date, clause or claim. Use these words only: 'At risk', 'Review', 'Payable',
'Potential inconsistency', 'Supported'. Never say 'wrongly deducted'. No legal advice."""


def _guard(texts: list[str], allowed: set[str]) -> list[str]:
    bad = set()
    for t in texts:
        bad |= evidence.unsupported_numbers(t, allowed)
    return sorted(bad)


def _note_unsupported(n):
    a = llm.acc()
    a.setdefault("unsupported_numbers", 0)
    a["unsupported_numbers"] += n


def explain(estimate: dict) -> dict:
    items = [i for i in estimate["items"] if i["verdict"] in ("AT_RISK", "REVIEW")]
    if not items:
        return {}
    payload = [{k: i.get(k) for k in ("line_id", "description", "amount", "payable", "at_risk", "rule_type", "formula",
                                      "verdict", "policy_quote", "notes")} for i in items]
    allowed = evidence.allowed_numbers(payload)
    fallback = {i["line_id"]: f"{i['description']}: {i['formula']}." + (" Needs review: " + "; ".join(i["notes"]) if i["notes"] else "")
                for i in items}
    for _ in range(2):
        try:
            r = llm.generate_json("generate", [f"Explain each finding in 1-2 sentences.\n{json.dumps(payload)}"], Explanations, STYLE)
        except Exception:
            break
        out = {e.line_id: e.text for e in r.explanations if e.line_id in fallback}
        bad = _guard(list(out.values()), allowed)
        if not bad:
            return {**fallback, **out}
        _note_unsupported(len(bad))
    return fallback


def _letter(kind: str, payload: dict, template: Letter) -> dict:
    allowed = evidence.allowed_numbers(payload)
    for _ in range(2):
        try:
            r = llm.generate_json("generate", [f"Draft the {kind}. Input:\n{json.dumps(payload)}"], Letter,
                                  STYLE + "\nWrite in the first person AS THE POLICYHOLDER, addressed to the insurer "
                                  "(e.g. 'To the Grievance Officer, <insurer>'). Format amounts as 'Rs 28,000'. Sign off with "
                                  "placeholders [Your name], [Policy number], [Claim number]. Leave placeholders for anything not in the input.")
        except Exception:
            break
        bad = _guard([r.subject, r.body], allowed)
        if not bad:
            return dict(r.model_dump(), source="generated")
        _note_unsupported(len(bad))
    return dict(template.model_dump(), source="template")


def cover_letter(policy_id: str, estimate: dict, checks: dict) -> dict:
    p = profile(policy_id)
    payload = dict(insurer=p["insurer"], product=p["product"], total_billed=estimate["total_billed"],
                   missing=[c["item"] for c in checks.get("completeness", []) if not c["present"]])
    body = (f"To the Claims Department, {p['insurer']}\n\nPlease find enclosed my reimbursement claim under {p['product']} "
            f"for hospital expenses of Rs {estimate['total_billed']:,}. The enclosed documents are listed in the index."
            + (f"\nDocuments still to follow: {', '.join(payload['missing'])}." if payload["missing"] else "")
            + "\n\nRegards,\n[Your name]\n[Policy number]")
    return _letter("cover letter for a reimbursement claim submission", payload,
                   Letter(subject=f"Reimbursement claim - {p['product']}", body=body))


def grievance_letter(policy_id: str, rows: list[dict], timeline: dict | None) -> dict:
    p = profile(policy_id)
    payload = dict(insurer=p["insurer"], product=p["product"], findings=[{k: r.get(k) for k in (
        "description", "estimated", "paid", "variance", "formula", "policy_quote")} for r in rows], timeline=timeline or {})
    lines = "\n".join(f"- {r['description']}: estimated payable Rs {r['estimated']:,}, paid Rs {r['paid']:,} "
                      f"(variance Rs {r['variance']:,}). Policy text: \"{r.get('policy_quote') or 'see policy wording'}\""
                      for r in rows)
    body = (f"To the Grievance Officer, {p['insurer']}\n\nI request a review of the settlement of my claim under "
            f"{p['product']}. The following deductions appear to be potential inconsistencies with the policy wording:\n"
            f"{lines}\n\nPlease review and share the basis of these deductions.\n\nRegards,\n[Your name]\n[Policy number] [Claim number]")
    return _letter("grievance letter requesting review of a claim settlement", payload,
                   Letter(subject=f"Request for review of claim settlement - {p['product']}", body=body))
