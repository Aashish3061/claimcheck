"""Stage 2 (code only): completeness, cross-document consistency, submission deadline."""
from datetime import date, timedelta
from difflib import SequenceMatcher
from claimcheck.rules.engine import profile

BILL = ("final_bill", "itemised_bill")


def check_completeness(policy_id: str, doc_types: list[str], has_diagnostics: bool) -> list[dict]:
    have = set(doc_types)
    need = [("final bill (itemised)", any(d in have for d in BILL)), ("discharge summary", "discharge_summary" in have)]
    if "pharmacy_bill" in have:
        need.append(("prescription supporting the pharmacy bill", "prescription" in have))
    if has_diagnostics:
        need.append(("investigation reports", "investigation_report" in have))
    return [dict(item=n, present=ok, verdict="OK" if ok else "MISSING") for n, ok in need]


def _norm_name(s):
    return " ".join((s or "").lower().replace(".", " ").split())


def check_consistency(docs: list[dict]) -> list[dict]:
    out = []
    names = [(d["doc_type"], d.get("patient_name")) for d in docs if d.get("patient_name")]
    names.sort(key=lambda x: x[0] not in BILL)  # compare everything against the bill's name
    for (t1, n1), (t2, n2) in ((names[0], n) for n in names[1:]):
        r = SequenceMatcher(None, _norm_name(n1), _norm_name(n2)).ratio()
        if r < 1.0:
            out.append(dict(check="patient_name", verdict="REVIEW" if r >= 0.6 else "MISMATCH",
                            detail=f"'{n1}' ({t1}) vs '{n2}' ({t2})"))
    for k in ("admission_date", "discharge_date"):
        vals = [(d["doc_type"], d.get(k)) for d in docs if d.get(k)]
        if len({v for _, v in vals}) > 1:
            out.append(dict(check=k, verdict="MISMATCH", detail="; ".join(f"{t}: {v}" for t, v in vals)))
    for d in docs:
        if d["doc_type"] in BILL and d.get("stated_total") is not None and d.get("line_total") is not None \
                and abs(d["stated_total"] - d["line_total"]) > 1:
            out.append(dict(check="bill_total", verdict="MISMATCH",
                            detail=f"stated Rs {d['stated_total']:,} vs line items Rs {d['line_total']:,}"))
    return out


def check_deadline(policy_id: str, discharge_date: str | None, today: str | None = None) -> dict:
    p = profile(policy_id)
    days = p.get("submission_deadline_days_from_discharge")
    if not isinstance(days, int):
        return dict(verdict="REVIEW", detail="Check your policy's claim submission deadline")
    if not discharge_date:
        return dict(verdict="REVIEW", detail=f"Submit within {days} days of discharge")
    due = date.fromisoformat(discharge_date) + timedelta(days=days)
    left = (due - date.fromisoformat(today or date.today().isoformat())).days
    return dict(verdict="OK" if left >= 0 else "LATE", due_date=due.isoformat(), days_left=left,
                detail=f"Submit within {days} days of discharge (source: {p.get('deadline_source')})")


def run_checks(policy_id: str, docs: list[dict], has_diagnostics: bool, today: str | None = None) -> dict:
    bill = next((d for d in docs if d["doc_type"] in BILL), None) or {}
    return dict(completeness=check_completeness(policy_id, [d["doc_type"] for d in docs], has_diagnostics),
                consistency=check_consistency(docs),
                deadline=check_deadline(policy_id, bill.get("discharge_date"), today))
