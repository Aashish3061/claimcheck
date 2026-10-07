"""Stage 1: classify + extract one uploaded document (PDF or image) into ExtractedDoc."""
from datetime import date
from claimcheck import llm
from claimcheck.schemas import ExtractedDoc

SYSTEM = """You read Indian hospital and insurance documents for a reimbursement claim.
Classify the document and extract its fields exactly as printed. Rules:
- doc_type: pick the closest enum value.
- Dates as YYYY-MM-DD. Amounts as integer rupees without commas.
- line_items only for bills: one per billed line, in order, line_id L1, L2, ...; category from the enum:
  room = room rent / room, boarding and nursing packages; icu = ICU charges; nursing; medical_practitioner_fees =
  doctor visits, consultation, surgeon, anaesthetist; ot_charges; pharmacy (medicines); consumables; implants;
  medical_devices; diagnostics = lab, imaging, investigations; non_payable_candidate = telephone, television,
  attendant, laundry, food for attendants, toiletries, admission kit and similar comfort items; other.
  For room/ICU lines set room_days to the number of days billed.
- tariff: only for room tariff cards (category and rate per day).
- notes: copy any statement about charges varying by room category, verbatim.
- Do not compute or infer amounts that are not printed. Never invent values; use null when absent."""


def extract_document(data: bytes, mime: str) -> dict:
    doc = llm.generate_json("extract", [llm.user(llm.file_part(data, mime), "Extract this document.")], ExtractedDoc, SYSTEM)
    out = doc.model_dump()
    out["needs_confirmation"] = needs_confirmation(out)
    out["line_total"] = sum(i["amount"] for i in out["line_items"]) if out["line_items"] else None
    return out


def _bad_date(s):
    if not s:
        return True
    try:
        date.fromisoformat(s)
        return False
    except ValueError:
        return True


def needs_confirmation(d: dict) -> list[str]:
    """Computed in code (not model self-confidence): which fields the user must look at."""
    flags = []
    items = d.get("line_items") or []
    if d["doc_type"] in ("final_bill", "itemised_bill"):
        if d.get("stated_total") is not None and abs(sum(i["amount"] for i in items) - d["stated_total"]) > 1:
            flags.append("stated_total")
        for k in ("admission_date", "discharge_date"):
            if _bad_date(d.get(k)):
                flags.append(k)
        for i in items:
            if i["category"] == "other":
                flags.append(f"{i['line_id']}.category")
            if i["amount"] <= 0:
                flags.append(f"{i['line_id']}.amount")
            if i["category"] in ("room", "icu") and not i.get("room_days"):
                flags.append(f"{i['line_id']}.room_days")
    return flags
