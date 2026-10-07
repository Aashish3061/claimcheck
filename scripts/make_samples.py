"""Generate SYNTHETIC sample claim packs + ground truth for ClaimCheck tests.
All hospitals, patients and amounts are fictional. Policy terms mirror public wordings (see corpus/policy_profiles.json)."""
import json, os, datetime as dt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sample_claims")
BANNER = "SYNTHETIC TEST DOCUMENT - fictional hospital and patient - not a real bill or record"

CASES = {
 "S1": dict(policy_id="star_fho", sum_insured=400000, age=45, patient="Asha Example", hospital="Sample Care Hospital, Pune (fictional)",
   admit="2026-08-03", discharge="2026-08-07", diagnosis="Symptomatic cholelithiasis - laparoscopic cholecystectomy",
   room=dict(label="Room, boarding & nursing (Deluxe single)", per_day=8000, days=4), eligible_per_day=5000,
   eligible_source="Policy cap Rs 5,000/day for sum insured Rs 3-4 lakh",
   lines=[("Consultation / doctor visits","medical_practitioner_fees",12000),("Surgeon fee","medical_practitioner_fees",50000),
          ("Anaesthetist fee","medical_practitioner_fees",15000),("Operation theatre charges","ot_charges",40000),
          ("Pharmacy & consumables","pharmacy",28000),("Diagnostics (lab + ultrasound)","diagnostics",14000),
          ("Telephone charges","non_payable_candidate",600),("Attendant charges","non_payable_candidate",2400)],
   footer="Doctor visit, surgeon, anaesthetist and OT charges are billed as per room category.",
   docs=["final_bill","discharge_summary","pharmacy_bill","prescription","investigation_report"],
   names={}, dates={}),
 "S2": dict(policy_id="hdfc_optima_secure", sum_insured=500000, age=38, patient="Rohan Example", hospital="Lakeview Clinic, Nagpur (fictional)",
   admit="2026-08-10", discharge="2026-08-13", diagnosis="Acute gastroenteritis with moderate dehydration",
   room=dict(label="Room rent (Single AC)", per_day=6000, days=3), eligible_per_day=None,
   eligible_source="Room rent at actuals (no limit in schedule)",
   lines=[("Nursing charges","nursing",4500),("Consultation / doctor visits","medical_practitioner_fees",6000),
          ("Pharmacy & consumables","pharmacy",15500),("Diagnostics (lab)","diagnostics",9000),
          ("Television charges","non_payable_candidate",300)],
   footer="", docs=["final_bill","discharge_summary","pharmacy_bill","investigation_report"],  # prescription deliberately MISSING
   names={"discharge_summary":"Rohan Exampel"}, dates={"discharge_summary":"2026-08-14"}),
 "S3": dict(policy_id="niva_reassure2", sum_insured=1000000, age=52, patient="Meera Example", hospital="Riverside Hospital, Indore (fictional)",
   admit="2026-09-01", discharge="2026-09-04", diagnosis="Dengue fever with thrombocytopenia",
   room=dict(label="Room rent (Deluxe)", per_day=7000, days=2), eligible_per_day=4000,
   eligible_source="Eligible category: single private room; hospital tariff for that category Rs 4,000/day (tariff card)",
   lines=[("ICU charges (1 day)","icu",12000),("Nursing charges","nursing",5000),("Medical practitioner fees","medical_practitioner_fees",9000),
          ("Pharmacy & consumables","pharmacy",11000),("Diagnostics (lab)","diagnostics",6500)],
   footer="Nursing and doctor visit charges vary by room category.",
   docs=["final_bill","discharge_summary","pharmacy_bill","prescription","investigation_report","tariff_card"],
   names={}, dates={}),
}
import random as _r
_rng = _r.Random(20261007)
_NAMES = ["Kavya Example", "Arjun Example", "Neha Example", "Vikram Example", "Ishaan Example", "Pooja Example",
          "Rahul Example", "Divya Example", "Sanjay Example", "Anita Example", "Farhan Example", "Leela Example"]
_HOSP = ["Greenfield Hospital, Jaipur (fictional)", "Harbour Clinic, Kochi (fictional)", "Sunrise Hospital, Lucknow (fictional)",
         "Maple Hospital, Bhopal (fictional)"]
_DX = ["Acute appendicitis - laparoscopic appendicectomy", "Community-acquired pneumonia", "Fracture of radius - closed reduction",
       "Dengue fever", "Kidney stone - ureteroscopy", "Acute gastroenteritis"]
for n in range(1, 13):
    pol = ["star_fho", "niva_reassure2", "hdfc_optima_secure"][n % 3]
    si = {"star_fho": _rng.choice([200000, 300000, 400000]), "niva_reassure2": 500000, "hdfc_optima_secure": 500000}[pol]
    days = _rng.randint(2, 5)
    rent = _rng.choice([3000, 4000, 5000, 6000, 7000, 8000, 9000])
    surg = n % 2 == 1
    lines = [("Consultation / doctor visits", "medical_practitioner_fees", _rng.randrange(4000, 15000, 500))]
    if pol != "star_fho":
        lines.insert(0, ("Nursing charges", "nursing", _rng.randrange(2000, 9000, 500)))
    if surg:
        lines += [("Surgeon fee", "medical_practitioner_fees", _rng.randrange(20000, 60000, 1000)),
                  ("Operation theatre charges", "ot_charges", _rng.randrange(15000, 45000, 1000))]
    lines += [("Pharmacy & consumables", "pharmacy", _rng.randrange(6000, 30000, 500)),
              ("Diagnostics (lab)", "diagnostics", _rng.randrange(3000, 15000, 500))]
    if n % 4 in (1, 2):
        lines.append(_rng.choice([("Telephone charges", "non_payable_candidate", 400), ("Attendant charges", "non_payable_candidate", 1800),
                                  ("Television charges", "non_payable_candidate", 500)]))
    elig = {"star_fho": (2000 if si <= 200000 else 5000), "niva_reassure2": 4000, "hdfc_optima_secure": None}[pol]
    docs = ["final_bill", "discharge_summary", "pharmacy_bill", "prescription", "investigation_report"] + (["tariff_card"] if pol == "niva_reassure2" else [])
    if n % 5 == 0:
        docs.remove("prescription")
    a = f"2026-0{_rng.randint(6, 9)}-{_rng.randint(10, 20)}"
    d = (dt.date.fromisoformat(a) + dt.timedelta(days=days)).isoformat()
    CASES[f"V{n:02d}"] = dict(policy_id=pol, sum_insured=si, age=_rng.randint(25, 60), patient=_NAMES[n - 1], hospital=_rng.choice(_HOSP),
        admit=a, discharge=d, diagnosis=_rng.choice(_DX),
        room=dict(label="Room rent" + (" (room, boarding & nursing)" if pol == "star_fho" else ""), per_day=rent, days=days),
        eligible_per_day=elig, eligible_source="variant", lines=lines,
        footer="Doctor visit, surgeon, anaesthetist and OT charges are billed as per room category." if pol != "hdfc_optima_secure" else "",
        docs=docs, names={}, dates={})
SPLIT = {**{c: "dev" for c in ["S1", "S2", "S3", "V01", "V02", "V03", "V04", "V05", "V06"]},
         **{c: "val" for c in ["V07", "V08", "V09"]}, **{c: "test" for c in ["V10", "V11", "V12"]}}

# Heads that are 'associated medical expenses' per profile (see policy_profiles.json; S1 Star list TO VERIFY)
ASSOC = {"star_fho": {"room","medical_practitioner_fees","ot_charges"},
         "niva_reassure2": {"room","nursing","medical_practitioner_fees","ot_charges"},
         "hdfc_optima_secure": {"room","nursing","medical_practitioner_fees","ot_charges"}}

def estimate(c, room_per_day=None):
    """Independent reference implementation (ground truth). Integer rupees; ratio applied per head, rounded half-up."""
    r = room_per_day or c["room"]["per_day"]; days = c["room"]["days"]; elig = c["eligible_per_day"]
    heads = [(c["room"]["label"], "room", r * days)] + c["lines"]
    ratio = 1.0 if (elig is None or r <= elig) else elig / r
    out, payable, at_risk = [], 0, 0
    for desc, cat, amt in heads:
        if cat == "non_payable_candidate":
            pay, rule = 0, "NON_PAYABLE_LIST_I"
        elif cat in ASSOC[c["policy_id"]] and ratio < 1:
            pay, rule = int(amt * ratio + 0.5), "PROPORTIONATE_DEDUCTION"
        else:
            pay, rule = amt, None
        out.append(dict(item=desc, category=cat, amount=amt, payable=pay, at_risk=amt - pay, rule_type=rule))
        payable += pay; at_risk += amt - pay
    return dict(total_billed=payable + at_risk, payable=payable, at_risk=at_risk, ratio=round(ratio, 6), items=out)

def write_pdf(path, title, c, lines):
    cv = canvas.Canvas(path, pagesize=A4); w, h = A4
    cv.setFillColorRGB(0.8, 0, 0); cv.setFont("Helvetica-Bold", 9); cv.drawString(36, h - 30, BANNER); cv.setFillColorRGB(0, 0, 0)
    cv.setFont("Helvetica-Bold", 14); cv.drawString(36, h - 60, c["hospital"]); cv.setFont("Helvetica-Bold", 12); cv.drawString(36, h - 80, title)
    y = h - 110; cv.setFont("Helvetica", 10)
    for ln in lines:
        cv.drawString(36, y, ln); y -= 15
    cv.setFont("Helvetica-Oblique", 8); cv.drawString(36, 30, BANNER); cv.save()

def docs_for(cid, c):
    nm = lambda d: c["names"].get(d, c["patient"]); dis = lambda d: c["dates"].get(d, c["discharge"])
    hdr = lambda d: [f"Patient: {nm(d)}   Age: {c['age']}", f"Admission: {c['admit']}   Discharge: {dis(d)}", ""]
    room_amt = c["room"]["per_day"] * c["room"]["days"]
    bill = hdr("final_bill") + ["ITEMISED FINAL BILL", f"{c['room']['label']}: {c['room']['days']} days x Rs {c['room']['per_day']:,} = Rs {room_amt:,}"]
    bill += [f"{d}: Rs {a:,}" for d, _, a in c["lines"]]
    total = room_amt + sum(a for _, _, a in c["lines"])
    bill += ["", f"TOTAL: Rs {total:,}", c["footer"]]
    ph = [l for l in c["lines"] if l[1] == "pharmacy"][0][2]
    dg = [l for l in c["lines"] if l[1] == "diagnostics"][0][2]
    d = {
     "final_bill": ("Final Bill", bill),
     "discharge_summary": ("Discharge Summary", hdr("discharge_summary") + [f"Diagnosis: {c['diagnosis']}", "Condition at discharge: stable", "Advice: review after 7 days", "Treating doctor: Dr. Sample (fictional)"]),
     "pharmacy_bill": ("Pharmacy Bill", hdr("pharmacy_bill") + ["Medicines and consumables as per prescription", f"Total: Rs {ph:,}"]),
     "prescription": ("Prescription", hdr("prescription") + ["Rx: medicines as dispensed (see pharmacy bill)", "Signed: Dr. Sample (fictional)"]),
     "investigation_report": ("Investigation Reports", hdr("investigation_report") + ["Lab and imaging reports enclosed", f"Billed: Rs {dg:,}"]),
     "tariff_card": ("Room Tariff Card", [f"Single private room: Rs {(c['eligible_per_day'] or 0):,}/day", f"Deluxe room: Rs {max(c['room']['per_day'], (c['eligible_per_day'] or 0) + 1000):,}/day", c["footer"]]),
    }
    return {k: d[k] for k in c["docs"]}

def main():
    os.makedirs(OUT, exist_ok=True); truth = {}
    for cid, c in CASES.items():
        os.makedirs(os.path.join(OUT, cid), exist_ok=True)
        for k, (title, lines) in docs_for(cid, c).items():
            write_pdf(os.path.join(OUT, cid, f"{k}.pdf"), title, c, lines)
        e = estimate(c)
        t = dict(policy_id=c["policy_id"], sum_insured=c["sum_insured"], eligible_room_rent_per_day=c["eligible_per_day"],
                 eligible_source=c["eligible_source"], estimate=e)
        if c["eligible_per_day"]:
            t["whatif_room_related_at_risk"] = {str(r): estimate(c, r)["at_risk"] - sum(i["at_risk"] for i in e["items"] if i["rule_type"] == "NON_PAYABLE_LIST_I")
                           for r in (c["eligible_per_day"] - 1000, c["eligible_per_day"], c["eligible_per_day"] + 1000, c["room"]["per_day"])}
        if cid == "S2":
            t["expected_checks"] = ["MISSING: prescription supporting pharmacy bill",
                                    "MISMATCH: discharge date 2026-08-13 (bill) vs 2026-08-14 (discharge summary)",
                                    "MISMATCH: patient name 'Rohan Example' vs 'Rohan Exampel' (review)"]
            t["submission_deadline"] = "2026-09-12 (30 days from discharge per policy clause; verify)"
        if cid == "S1":
            t["submission_deadline"] = "2026-08-22 (15 days from discharge per starhealth.in/claims; verify)"
            # Typed settlement for the after-settlement audit test (NOT a document): insurer also pro-rated pharmacy + diagnostics
            ins = {i["item"]: (int(i["amount"] * e["ratio"] + 0.5) if i["category"] in ("pharmacy", "diagnostics") else i["payable"]) for i in e["items"]}
            paid = sum(ins.values()); intim, sub, setl = "2026-08-04", "2026-08-18", "2026-09-10"
            days_late_basis = (dt.date.fromisoformat(setl) - dt.date.fromisoformat(sub)).days
            int_days = (dt.date.fromisoformat(setl) - dt.date.fromisoformat(intim)).days
            test_bank_rate = 0.05  # TEST VALUE ONLY - not RBI's actual bank rate
            t["settlement_input"] = dict(per_head_paid=ins, total_paid=paid, intimation_date=intim, submission_date=sub, settlement_date=setl)
            t["expected_audit"] = dict(variance=e["payable"] - paid,
                flags=[dict(item=i["item"], variance=i["payable"] - ins[i["item"]], verdict="POTENTIAL_INCONSISTENCY")
                       for i in e["items"] if i["payable"] != ins[i["item"]]],
                settlement_days_after_submission=days_late_basis, beyond_15_days=days_late_basis > 15,
                indicative_interest=dict(rate=f"bank rate (test {test_bank_rate:.0%}) + 2%", days=int_days,
                                         amount=int(paid * (test_bank_rate + 0.02) * int_days / 365 + 0.5)))
        truth[cid] = t
    json.dump({k: v for k, v in truth.items() if k.startswith("S")}, open(os.path.join(OUT, "expected.json"), "w"), indent=2)
    cases = {}
    for cid, c in CASES.items():
        items = [dict(description=c["room"]["label"], category="room", amount=c["room"]["per_day"] * c["room"]["days"], room_days=c["room"]["days"])]
        items += [dict(description=d, category=cat, amount=a) for d, cat, a in c["lines"]]
        cases[cid] = dict(case_id=cid, split=SPLIT[cid], policy_id=c["policy_id"], sum_insured=c["sum_insured"],
                          eligible_room_rent_per_day=c["eligible_per_day"] if c["policy_id"] == "niva_reassure2" else None,
                          docs=c["docs"], patient=c["patient"], admit=c["admit"], discharge=c["discharge"],
                          doc_names=c["names"], doc_dates=c["dates"], items=items, expected=truth[cid]["estimate"],
                          prescription_missing="pharmacy_bill" in c["docs"] and "prescription" not in c["docs"])
    json.dump(cases, open(os.path.join(ROOT, "eval", "cases.json"), "w"), indent=1)
    print(json.dumps({k: (v["estimate"]["total_billed"], v["estimate"]["payable"], v["estimate"]["at_risk"], v.get("whatif_room_related_at_risk"), v.get("expected_audit", {}).get("variance")) for k, v in truth.items()}, indent=1))

if __name__ == "__main__":
    main()
