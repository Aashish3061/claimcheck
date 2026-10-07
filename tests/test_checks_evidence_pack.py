import asyncio, json, os, re
from claimcheck import checks, config, evidence, pack
from claimcheck.rules import engine

CASES = json.load(open(os.path.join(config.ROOT, "eval", "cases.json")))


def test_s2_expected_findings():
    c = CASES["S2"]
    docs = [dict(doc_type=d, patient_name=c["doc_names"].get(d, c["patient"]), admission_date=c["admit"],
                 discharge_date=c["doc_dates"].get(d, c["discharge"])) for d in c["docs"]]
    r = checks.run_checks("hdfc_optima_secure", docs, True, today="2026-08-20")
    missing = [x["item"] for x in r["completeness"] if not x["present"]]
    assert missing == ["prescription supporting the pharmacy bill"]
    kinds = {x["check"]: x["verdict"] for x in r["consistency"]}
    assert kinds == {"patient_name": "REVIEW", "discharge_date": "MISMATCH"}
    assert r["deadline"]["due_date"] == "2026-09-12"


def test_quote_check():
    chunk = "Associated medical expenses do not include Cost of pharmacy and consumables, Cost of implants"
    assert evidence.quote_ok("associated medical expenses do NOT include cost of pharmacy", chunk)
    assert not evidence.quote_ok("pharmacy is subject to proportionate deduction", chunk)
    assert not evidence.quote_ok("pharmacy", chunk)  # too short to be evidence


def test_number_guard():
    allowed = evidence.allowed_numbers({"at_risk": 58875, "formula": "Rs 32,000 x (5,000 / 8,000)"})
    assert not evidence.unsupported_numbers("Rs 58,875 is at risk; 5,000 vs 8,000 per day", allowed)
    assert evidence.unsupported_numbers("Rs 60,000 is at risk", allowed) == {"60000"}
    assert evidence.numbers_in("Rs 1,35,125") == {"135125"}


def test_pack_pdf_builds():
    items = [dict(line_id="L1", description="Room", category="room", amount=32000, room_days=4, confirmed=True)]
    e = engine.estimate_settlement("star_fho", 400000, items, [dict(line_id="L1", rule_type="ROOM_RENT_CAP")], evidence={"L1": True})
    pdf = pack.build_pack_pdf("star_fho", e, {"completeness": [], "consistency": []}, {"Name": "Test"}, ["final_bill"],
                              {"subject": "Claim", "body": "Body"})
    assert pdf[:4] == b"%PDF" and len(pdf) > 1500


def test_mcp_tools_registered():
    from mcp_server.server import mcp
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"retrieve_policy_clause", "estimate_settlement", "simulate_whatif", "settlement_timeline"} <= names


def test_diagram_routes_exist():
    """docs/architecture.mmd must only name routes that exist in app.py."""
    src = open(os.path.join(config.ROOT, "app.py")).read()
    routes = set(re.findall(r'@app\.(?:get|post)\("([^"]+)"', src))
    named = set(re.findall(r"(/api/[a-z_]+)", open(os.path.join(config.ROOT, "docs", "architecture.mmd")).read()))
    assert named and named <= routes, named - routes
