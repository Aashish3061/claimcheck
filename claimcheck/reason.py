"""Stage 3+4: retrieve + reason. The function-calling agent maps each confirmed line item to a rule type with a
verbatim quote; evidence.py then verifies every quote against the stored chunk. The model never outputs amounts."""
import json
from claimcheck import db, evidence, llm, rag
from claimcheck.rules.engine import profile
from claimcheck.schemas import Assignments

RULES_TEXT = """Rule types:
- ROOM_RENT_CAP: the room line when actual room rent exceeds the policy's eligible limit.
- PROPORTIONATE_DEDUCTION: an 'associated medical expense' head (as the policy defines it) reduced in proportion to eligible/actual room rent.
- NO_DEDUCTION: the policy clause shows this head is payable in full (e.g. excluded from proportionate deduction).
- NON_PAYABLE_LIST_I: an optional/non-payable item in List I of Annexure I.
- SUBSUMED_LIST_II_IV: an item that Lists II-IV say is subsumed into room, procedure or treatment charges.
- COPAY / DEDUCTIBLE: only if the policy wording states one that applies.
- UNKNOWN: no returned chunk governs the item."""

SYSTEM_TOOLS = f"""You are the reasoning step of ClaimCheck, an Indian health-insurance claim checker.
Use the tools to find the policy clauses and IRDAI items that govern each bill line. Call several tools in one turn
when you can. Stop calling tools once you have the governing text for every line.
{RULES_TEXT}"""

SYSTEM_ASSIGN = f"""You assign exactly one rule_type to each bill line, using ONLY the provided chunks.
{RULES_TEXT}
For each line give policy_chunk_id and policy_quote: a short sentence copied VERBATIM (character for character) from that
policy chunk which states the rule. For NON_PAYABLE_LIST_I / SUBSUMED_LIST_II_IV also give regulatory_chunk_id and
regulatory_quote from the matching Annexure I item chunk, and non_payable_list_no; their policy_quote should be the
item exactly as printed in the policy wording's own list of non-medical/non-payable items (e.g. "TELEPHONE CHARGES"). If no provided chunk governs a line,
use UNKNOWN with null quotes. Never output amounts or calculations."""

SEED_QUERIES = ["room rent limit eligible room category proportionate deduction associated medical expenses",
                "associated medical expenses do not include pharmacy consumables implants medical devices diagnostics ICU"]


def _items_text(items):
    return json.dumps([{k: i[k] for k in ("line_id", "description", "category", "room_days") if k in i} for i in items])


def _chunks_text(chunks: dict) -> str:
    return "\n\n".join(f"[chunk_id={c['chunk_id']} | {c.get('doc_type')} | status={c.get('status')} | section={c.get('section')}"
                       f"{' | list_no=' + str(c['list_no']) if c.get('list_no') else ''}]\n{c.get('text') or c.get('content')}"
                       for c in chunks.values())


def gather_rag(policy_id: str, items: list[dict]) -> dict:
    """Deterministic seed retrieval + the function-calling agent's own retrievals."""
    chunks = {}
    for q in SEED_QUERIES:
        for r in rag.retrieve_policy_clause(policy_id, q):
            chunks[r["chunk_id"]] = r
    for i in items:
        if i["category"] in ("non_payable_candidate", "other", "consumables"):
            for r in rag.find_non_payable_item(i["description"]):
                chunks[r["chunk_id"]] = r
            # policy wordings print the non-payable lists themselves: find this item in the policy's own list
            for r in rag.retrieve_policy_clause(policy_id, f"{i['description']} list of non-medical items not payable")[:2]:
                chunks[r["chunk_id"]] = r
    first = (f"Policy: {policy_id} ({profile(policy_id)['product']}). Bill lines:\n{_items_text(items)}\n"
             f"Already retrieved chunk ids: {list(chunks)}. Retrieve anything else you need.")
    try:
        for res in llm.tool_loop("reason", SYSTEM_TOOLS, first, rag.TOOLS):
            for r in res["result"] if isinstance(res["result"], list) else []:
                if isinstance(r, dict) and r.get("chunk_id"):
                    chunks[r["chunk_id"]] = r
    except Exception:
        pass  # seeds are enough to continue; failure is logged in runs
    return chunks


def gather_fulltext(policy_id: str, max_chars: int = 120000) -> dict:
    """Used by the v2 pipeline (no retrieval): the policy wording in order, truncated."""
    rows = db.rest("GET", "corpus_chunks", params={"select": "chunk_id,doc_type,status,section,content",
                                                   "policy_id": f"eq.{policy_id}", "order": "id"}) or []
    rows += db.rest("GET", "corpus_chunks", params={"select": "chunk_id,doc_type,status,section,content,list_no",
                                                    "doc_type": "eq.non_payable_item", "order": "id"}) or []
    out, n = {}, 0
    for r in rows:
        n += len(r["content"])
        if n > max_chars:
            break
        out[r["chunk_id"]] = r
    return out


def assign_rules(policy_id: str, items: list[dict], mode: str = "rag") -> dict:
    chunks = gather_rag(policy_id, items) if mode == "rag" else gather_fulltext(policy_id)
    res = llm.generate_json("reason", [f"Policy: {policy_id}. Bill lines:\n{_items_text(items)}\n\nChunks:\n{_chunks_text(chunks)}"],
                            Assignments, SYSTEM_ASSIGN)
    assigns = [a.model_dump() for a in res.assignments]
    ev, ev_detail = verify(policy_id, assigns)
    return dict(assignments=assigns, evidence=ev, evidence_detail=ev_detail, chunks_considered=len(chunks))


def verify(policy_id: str, assigns: list[dict]):
    """Evidence check against the stored chunk text (not the model's copy)."""
    ids = [a.get("policy_chunk_id") for a in assigns] + [a.get("regulatory_chunk_id") for a in assigns]
    stored = rag.get_chunks(ids)
    ev, detail = {}, {}
    for a in assigns:
        pc = stored.get(a.get("policy_chunk_id") or "")
        ok_policy = bool(pc) and pc["doc_type"] == "policy_wording" and pc.get("policy_id") == policy_id \
            and evidence.quote_ok(a.get("policy_quote"), pc["content"])
        ok = ok_policy
        if a["rule_type"] in ("NON_PAYABLE_LIST_I", "SUBSUMED_LIST_II_IV"):
            rc = stored.get(a.get("regulatory_chunk_id") or "")
            want = 1 if a["rule_type"] == "NON_PAYABLE_LIST_I" else (2, 3, 4)
            ok = ok and bool(rc) and rc["doc_type"] == "non_payable_item" and \
                (rc.get("list_no") == want if want == 1 else rc.get("list_no") in want) and \
                evidence.quote_ok(a.get("regulatory_quote"), rc["content"], min_len=4)
        if pc:
            a["policy_section"], a["policy_title"] = pc.get("section"), pc.get("title")
        rc = stored.get(a.get("regulatory_chunk_id") or "")
        if rc:
            a["regulatory_status"], a["regulatory_ref"] = rc.get("status"), rc.get("ref_no")
        ev[a["line_id"]] = ok
        detail[a["line_id"]] = dict(policy_quote_verified=ok_policy, overall=ok)
    return ev, detail
