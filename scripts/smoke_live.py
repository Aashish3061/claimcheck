"""End-to-end smoke test against a deployed URL with sample S1. Usage: python scripts/smoke_live.py https://claimcheck-pi.vercel.app"""
import json, os, sys, uuid
import httpx

base = sys.argv[1].rstrip("/")
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
h = {"X-Session-Id": str(uuid.uuid4())}
docs = []
for n in ["final_bill", "discharge_summary", "pharmacy_bill", "prescription", "investigation_report"]:
    with open(f"{root}/sample_claims/S1/{n}.pdf", "rb") as f:
        docs.append(httpx.post(f"{base}/api/extract", files={"file": (f"{n}.pdf", f, "application/pdf")}, headers=h, timeout=120).json())
bill = next(d for d in docs if d["doc_type"] in ("final_bill", "itemised_bill"))  # same rule as the app
items = [dict(i, confirmed=True) for i in bill["line_items"]]
r = httpx.post(f"{base}/api/estimate", json=dict(policy_id="star_fho", sum_insured=400000, items=items), headers=h, timeout=300).json()
e = r["estimate"]
print("payable", e["payable"], "at_risk", e["at_risk"])
assert (e["payable"], e["at_risk"]) == (135125, 58875), "estimate mismatch"
w = httpx.post(f"{base}/api/whatif", json=dict(policy_id="star_fho", sum_insured=400000, items=items, assignments=r["assignments"],
                                                room_rent_values=[6000]), headers=h, timeout=60).json()
assert w[0]["at_risk_room_related"] == 23500, w
print("smoke test passed")
