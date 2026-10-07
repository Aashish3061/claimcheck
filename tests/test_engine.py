"""Engine must reproduce sample_claims/expected.json exactly (independent reference implementation)."""
import json, os
import pytest
from claimcheck import config
from claimcheck.rules import engine

ROOT = config.ROOT
TRUTH = json.load(open(os.path.join(ROOT, "sample_claims", "expected.json")))


def case_inputs(cid):
    t = TRUTH[cid]
    items, assigns, ev = [], [], {}
    for n, i in enumerate(t["estimate"]["items"], 1):
        lid = f"L{n}"
        days = None
        if i["category"] == "room":
            days = {"S1": 4, "S2": 3, "S3": 2}[cid]
        items.append(dict(line_id=lid, description=i["item"], category=i["category"], amount=i["amount"],
                          room_days=days, confirmed=True))
        rt = i["rule_type"] or "NO_DEDUCTION"
        if i["category"] == "room" and rt == "PROPORTIONATE_DEDUCTION":
            rt = "ROOM_RENT_CAP"
        assigns.append(dict(line_id=lid, rule_type=rt, policy_chunk_id="x", policy_quote="q"))
        ev[lid] = True
    return t, items, assigns, ev


@pytest.mark.parametrize("cid", ["S1", "S2", "S3"])
def test_estimate_matches_truth(cid):
    t, items, assigns, ev = case_inputs(cid)
    e = engine.estimate_settlement(t["policy_id"], t["sum_insured"], items, assigns,
                                   t["eligible_room_rent_per_day"] if cid == "S3" else None, evidence=ev)
    assert e["total_billed"] == t["estimate"]["total_billed"]
    assert e["payable"] == t["estimate"]["payable"]
    assert e["at_risk"] == t["estimate"]["at_risk"]
    for got, exp in zip(e["items"], t["estimate"]["items"]):
        assert (got["amount"], got["payable"], got["at_risk"]) == (exp["amount"], exp["payable"], exp["at_risk"])
    if cid == "S1":
        assert e["eligible_room_rent_per_day"] == 5000  # from the Star FHO band, not user input


@pytest.mark.parametrize("cid", ["S1", "S3"])
def test_whatif(cid):
    t, items, assigns, ev = case_inputs(cid)
    elig = t["eligible_room_rent_per_day"] if cid == "S3" else None
    vals = [int(v) for v in t["whatif_room_related_at_risk"]]
    res = engine.simulate_whatif(t["policy_id"], t["sum_insured"], items, assigns, elig, vals, ev)
    assert {str(r["room_rent_per_day"]): r["at_risk_room_related"] for r in res} == t["whatif_room_related_at_risk"]
    # property: 0 at/below cap, non-decreasing above
    grid = engine.simulate_whatif(t["policy_id"], t["sum_insured"], items, assigns, elig, list(range(1000, 15001, 500)), ev)
    cap = t["eligible_room_rent_per_day"]
    prev = -1
    for r in grid:
        if r["room_rent_per_day"] <= cap:
            assert r["at_risk_room_related"] == 0
        assert r["at_risk_room_related"] >= prev
        prev = r["at_risk_room_related"]
    # what-if at actual rent == main estimate
    actual = items[[i["category"] for i in items].index("room")]["amount"] // items[[i["category"] for i in items].index("room")]["room_days"]
    e = engine.estimate_settlement(t["policy_id"], t["sum_insured"], items, assigns, elig, evidence=ev)
    assert engine.simulate_whatif(t["policy_id"], t["sum_insured"], items, assigns, elig, [actual], ev)[0]["at_risk_total"] == e["at_risk"]


def test_audit_and_timeline_s1():
    t, items, assigns, ev = case_inputs("S1")
    e = engine.estimate_settlement("star_fho", 400000, items, assigns, evidence=ev)
    si = t["settlement_input"]
    paid = {f"L{n}": si["per_head_paid"][i["item"]] for n, i in enumerate(t["estimate"]["items"], 1)}
    a = engine.audit_settlement(e, paid)
    exp = t["expected_audit"]
    assert a["variance"] == exp["variance"] == 15750
    flagged = [(r["description"], r["variance"]) for r in a["rows"] if r["verdict"] == "POTENTIAL_INCONSISTENCY"]
    assert flagged == [(f["item"], f["variance"]) for f in exp["flags"]]
    tl = engine.settlement_timeline(si["intimation_date"], si["submission_date"], si["settlement_date"], si["total_paid"], 0.05)
    assert tl["settlement_days_after_submission"] == exp["settlement_days_after_submission"]
    assert tl["beyond_limit"] is True
    assert tl["indicative_interest"]["amount"] == exp["indicative_interest"]["amount"] == 847


def test_low_evidence_downgrades_to_review():
    t, items, assigns, ev = case_inputs("S1")
    e = engine.estimate_settlement("star_fho", 400000, items, assigns, evidence={})
    assert all(i["verdict"] in ("REVIEW", "PAYABLE") for i in e["items"])
    assert not any(i["verdict"] == "AT_RISK" for i in e["items"])


def test_model_disagreement_engine_wins():
    t, items, assigns, ev = case_inputs("S1")
    bad = [dict(a, rule_type="PROPORTIONATE_DEDUCTION") if items[n]["category"] == "pharmacy" else a for n, a in enumerate(assigns)]
    e = engine.estimate_settlement("star_fho", 400000, items, bad, evidence=ev)
    ph = next(i for i in e["items"] if i["category"] == "pharmacy")
    assert ph["payable"] == ph["amount"] and ph["verdict"] == "REVIEW"
    assert e["payable"] == 135125


def test_prices_cover_models():
    for m in set(config.MODELS.values()):
        assert m in config.PRICES
