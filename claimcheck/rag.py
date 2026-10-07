"""Hybrid retrieval (Postgres full-text + pgvector, merged by reciprocal rank fusion) over corpus_chunks."""
from claimcheck import db, llm

COLS = "chunk_id,doc_id,doc_type,policy_id,title,ref_no,doc_date,status,section,page,list_no,url,content"


def hybrid(query: str, doc_types: list[str], policy_id: str | None = None, k: int = 4) -> list[dict]:
    sem = 1.0
    try:
        emb = llm.embed([query], "query")[0]
    except Exception:  # embedding unavailable (quota/outage): degrade to full-text search only
        emb, sem = [0.0] * 768, 0.0
        llm.acc()["degraded_retrieval"] = True
    rows = db.rpc("hybrid_search", {"query_text": query, "query_embedding": emb, "match_count": k,
                                    "filter_doc_types": doc_types, "filter_policy_id": policy_id, "semantic_weight": sem})
    return rows or []


def _brief(rows, n=1200):
    return [{"chunk_id": r["chunk_id"], "doc_type": r.get("doc_type"), "section": r.get("section"), "status": r.get("status"),
             "list_no": r.get("list_no"), "title": r.get("title"), "text": (r.get("content") or "")[:n]} for r in rows]


# ----- the three tools exposed to Gemini (function calling) and to MCP -----
def retrieve_policy_clause(policy_id: str, query: str) -> list[dict]:
    """Search the selected policy's wording for the clause that governs a bill item or rule.
    Args: policy_id: policy identifier (e.g. star_fho). query: what to look for, e.g. 'room rent limit proportionate deduction'."""
    return _brief(hybrid(query, ["policy_wording"], policy_id, 4))


def retrieve_regulatory_rule(query: str) -> list[dict]:
    """Search IRDAI regulations and insurer claim checklists. Each result has a status: in_force or repealed.
    Args: query: the rule to look for, e.g. 'settled within fifteen days interest'."""
    return _brief(hybrid(query, ["regulation", "checklist"], None, 4))


def find_non_payable_item(description: str) -> list[dict]:
    """Look up a bill item in IRDAI Annexure I non-payable lists (List I optional items; Lists II-IV subsumed items).
    Args: description: the bill line description, e.g. 'telephone charges'."""
    return _brief(hybrid(description, ["non_payable_item"], None, 3), 300)


TOOLS = {"retrieve_policy_clause": retrieve_policy_clause, "retrieve_regulatory_rule": retrieve_regulatory_rule,
         "find_non_payable_item": find_non_payable_item}


def get_chunks(chunk_ids: list[str]) -> dict:
    ids = sorted({c for c in chunk_ids if c})
    if not ids:
        return {}
    quoted = ",".join('"' + c.replace('"', '') + '"' for c in ids)
    rows = db.rest("GET", "corpus_chunks", params={"select": COLS, "chunk_id": f"in.({quoted})"})
    return {r["chunk_id"]: r for r in rows or []}
