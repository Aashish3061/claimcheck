"""Stage 7 (code): the claim-pack PDF (cover letter, index, Part A form, exceptions). The browser merges it with the
user's original files using pdf-lib, so originals never need to be re-uploaded. Personal fields are never logged."""
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from claimcheck.rules.engine import profile

# Part A field list follows the IRDAI standard claim form (TPA Master Circular IRDAI/TPA/REG/CIR/130/06/2020, Annexure 30).
# TODO(HUMAN): verify section titles/fields against Annexure 30 text (see docs/human_checks.md).
PART_A = [
    ("A", "Details of primary insured", ["Policy no", "Certificate no", "Company / TPA ID no", "Name", "Address", "Phone", "Email"]),
    ("B", "Details of insurance history", ["Currently covered by any other mediclaim / health insurance (Y/N)"]),
    ("C", "Details of insured person hospitalised", ["Name", "Gender", "Age", "Date of birth", "Relationship to primary insured", "Occupation"]),
    ("D", "Details of hospitalisation", ["Name of hospital", "Room category", "Date of admission", "Date of discharge", "Injury / disease"]),
    ("E", "Details of claim", ["Hospital main bill", "Pre-hospitalisation expenses", "Post-hospitalisation expenses", "Total claimed"]),
    ("F", "Details of bills enclosed", ["(see document index)"]),
    ("G", "Details of primary insured's bank account", ["(fill by hand - ClaimCheck does not collect bank details)"]),
    ("H", "Declaration by the insured", ["Signature", "Date", "Place"]),
]
FOOTER = "Prepared with ClaimCheck - check your insurer's own claim form requirements. An estimate, not a guarantee or legal advice."


class _Doc:
    def __init__(self):
        self.buf = io.BytesIO()
        self.c = canvas.Canvas(self.buf, pagesize=A4)
        self.w, self.h = A4
        self.new_page(first=True)

    def new_page(self, first=False):
        if not first:
            self.c.showPage()
        self.c.setFont("Helvetica-Oblique", 7)
        self.c.drawString(36, 22, FOOTER)
        self.y = self.h - 50

    def line(self, text, size=10, bold=False, gap=14, indent=0):
        if self.y < 50:
            self.new_page()
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        for chunk in _wrap(str(text), 100 - indent // 6):
            self.c.drawString(36 + indent, self.y, chunk)
            self.y -= gap

    def bytes(self):
        self.c.save()
        return self.buf.getvalue()


def _wrap(s, n):
    out = []
    for para in s.split("\n"):
        while len(para) > n:
            cut = para.rfind(" ", 0, n)
            cut = cut if cut > 0 else n
            out.append(para[:cut]); para = para[cut:].lstrip()
        out.append(para)
    return out


def build_pack_pdf(policy_id: str, estimate: dict, checks: dict, personal: dict, docs_present: list[str], letter: dict) -> bytes:
    p = profile(policy_id)
    d = _Doc()
    d.line(letter.get("subject", "Reimbursement claim"), 13, True, 20)
    d.line(letter.get("body", ""), 10)
    d.new_page()
    d.line("Document index", 13, True, 20)
    for n, t in enumerate(docs_present, 1):
        d.line(f"{n}. {t.replace('_', ' ').title()}")
    missing = [c["item"] for c in checks.get("completeness", []) if not c["present"]]
    for m in missing:
        d.line(f"MISSING: {m}")
    d.new_page()
    d.line("Claim form - Part A (to be filled by the insured)", 13, True, 18)
    d.line(f"Insurer: {p['insurer']}   Product: {p['product']}   UIN: {p.get('uin')}", 9)
    auto = {"Name of hospital": personal.get("hospital_name"), "Date of admission": personal.get("admission_date"),
            "Date of discharge": personal.get("discharge_date"), "Hospital main bill": f"Rs {estimate.get('total_billed', 0):,}",
            "Total claimed": f"Rs {estimate.get('total_billed', 0):,}", "Room category": personal.get("room_category")}
    for sec, title, fields in PART_A:
        d.line(f"{sec}. {title}", 11, True, 16)
        for f in fields:
            val = personal.get(f) or auto.get(f) or ""
            d.line(f"{f}: {val}" + ("" if val else " ________________________"), 9, indent=12)
    d.new_page()
    d.line("Before you submit: exceptions and at-risk items", 13, True, 20)
    for c in checks.get("consistency", []):
        d.line(f"[{c['verdict']}] {c['check']}: {c['detail']}", 9)
    dl = checks.get("deadline") or {}
    if dl:
        d.line(f"[{dl.get('verdict')}] Deadline: {dl.get('detail')} {('- due ' + dl['due_date']) if dl.get('due_date') else ''}", 9)
    d.line(f"Estimated payable Rs {estimate.get('payable', 0):,}; at risk Rs {estimate.get('at_risk', 0):,}", 10, True, 16)
    for i in estimate.get("items", []):
        if i.get("at_risk"):
            d.line(f"[{i['verdict'].replace('_', ' ').title()}] {i['description']}: {i['formula']}", 9)
    return d.bytes()
