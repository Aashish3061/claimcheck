"""ClaimCheck MCP server (bonus, off the production path). Exposes the same functions the app uses - no duplicated logic.
Run:   python mcp_server/server.py                 (stdio)
Test:  npx @modelcontextprotocol/inspector python mcp_server/server.py
Needs GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SECRET_KEY in the environment for the retrieval tools."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastmcp import FastMCP
from claimcheck import checks, rag
from claimcheck.rules import engine

mcp = FastMCP("ClaimCheck")


@mcp.tool
def retrieve_policy_clause(policy_id: str, query: str) -> list[dict]:
    """Search a policy wording (star_fho, niva_reassure2, hdfc_optima_secure, care_supreme, icici_elevate) for the governing clause."""
    return rag.retrieve_policy_clause(policy_id, query)


@mcp.tool
def retrieve_regulatory_rule(query: str) -> list[dict]:
    """Search IRDAI circulars and insurer claim checklists (each result carries status in_force or repealed)."""
    return rag.retrieve_regulatory_rule(query)


@mcp.tool
def find_non_payable_item(description: str) -> list[dict]:
    """Look up a bill item in IRDAI Annexure I non-payable lists I-IV."""
    return rag.find_non_payable_item(description)


@mcp.tool
def check_completeness(policy_id: str, doc_types: list[str], has_diagnostics: bool = False) -> list[dict]:
    """Which documents are present or missing for a reimbursement claim."""
    return checks.check_completeness(policy_id, doc_types, has_diagnostics)


@mcp.tool
def estimate_settlement(policy_id: str, sum_insured: int, items: list[dict], assignments: list[dict],
                        eligible_room_rent_per_day: int | None = None) -> dict:
    """Deterministic estimate of the payable amount and amounts at risk (items: line_id, description, category, amount, room_days)."""
    return engine.estimate_settlement(policy_id, sum_insured, items, assignments, eligible_room_rent_per_day,
                                      evidence={a["line_id"]: True for a in assignments})


@mcp.tool
def simulate_whatif(policy_id: str, sum_insured: int, items: list[dict], assignments: list[dict],
                    eligible_room_rent_per_day: int | None, room_rent_values: list[int]) -> list[dict]:
    """Recompute amounts at risk for different room rents per day (no LLM)."""
    return engine.simulate_whatif(policy_id, sum_insured, items, assignments, eligible_room_rent_per_day, room_rent_values)


@mcp.tool
def settlement_timeline(intimation_date: str, submission_date: str, settlement_date: str, paid: int, bank_rate: float) -> dict:
    """15-day settlement rule and indicative interest at bank rate + 2% (IRDAI/PP&GR/CIR/MISC/117/9/2024)."""
    return engine.settlement_timeline(intimation_date, submission_date, settlement_date, paid, bank_rate)


if __name__ == "__main__":
    mcp.run()
