"""Corpus ingestion: PDF -> text -> clause-level chunks -> embeddings -> upsert into corpus_chunks.
Runs server-side (admin endpoint) because only Vercel can reach Gemini and Supabase."""
import io, re
from pypdf import PdfReader
from claimcheck import db, llm

# Metadata for every source document (see corpus/SOURCES.md). url = direct PDF link.
MANIFEST = {
    "irdai_master_health_2024": dict(doc_type="regulation", title="Master Circular on Health Insurance Business",
        issuer="IRDAI", ref_no="IRDAI/HLT/CIR/PRO/84/5/2024", doc_date="2024-05-29", status="in_force"),
    "irdai_pphi_master_2024": dict(doc_type="regulation", title="Master Circular on Protection of Policyholders' Interests",
        issuer="IRDAI", ref_no="IRDAI/PP&GR/CIR/MISC/117/9/2024", doc_date="2024-09-05", status="in_force"),
    "irdai_proportionate_2020": dict(doc_type="regulation", title="Norms on Proportionate Deductions (repealed 29 May 2024)",
        issuer="IRDAI", ref_no="IRDAI/HLT/REG/CIR/151/06/2020", doc_date="2020-06-11", status="repealed"),
    "irdai_standardisation_2020": dict(doc_type="regulation", title="Master Circular on Standardization of Health Insurance Products",
        issuer="IRDAI", ref_no="IRDAI/HLT/REG/CIR/193/07/2020", doc_date="2020-07-22", status="repealed"),
    "irdai_tpa_master_2020": dict(doc_type="claim_form", title="TPA Master Circular (Annexure 30: standard claim form)",
        issuer="IRDAI", ref_no="IRDAI/TPA/REG/CIR/130/06/2020", doc_date="2020-06-03", status="verify"),
    "star_fho": dict(doc_type="policy_wording", policy_id="star_fho", title="Star Health Family Health Optima - policy wording",
        issuer="Star Health", ref_no="SHAHLIP26046V092526", status="policy_wording"),
    "niva_reassure2": dict(doc_type="policy_wording", policy_id="niva_reassure2", title="Niva Bupa ReAssure 2.0 - policy wording",
        issuer="Niva Bupa", ref_no="NBHHLIP27054V032627", status="policy_wording"),
    "hdfc_optima_secure": dict(doc_type="policy_wording", policy_id="hdfc_optima_secure", title="HDFC ERGO my:Optima Secure - policy wording",
        issuer="HDFC ERGO", ref_no="HDFHLIP26058V082526", status="policy_wording"),
    "care_supreme": dict(doc_type="policy_wording", policy_id="care_supreme", title="Care Supreme - policy terms",
        issuer="Care Health", ref_no="see PDF", status="policy_wording"),
    "icici_elevate": dict(doc_type="policy_wording", policy_id="icici_elevate", title="ICICI Lombard Elevate - policy wording",
        issuer="ICICI Lombard", ref_no="ICIHLIP27057V062627", status="policy_wording"),
}

HEAD = re.compile(r"^\s*((?:\d{1,2}(?:\.\d{1,2}){0,3})|(?:[IVX]{1,4}\.)|(?:\([a-z]{1,3}\))|(?:[a-z]\)))\s+\S")
MAX_CHARS = 1500


def pdf_pages(data: bytes) -> list[str]:
    return [(p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages]


def ocr_pdf(data: bytes) -> list[str]:
    """Scanned PDFs: verbatim transcription with Gemini (logged as stage ocr)."""
    from claimcheck.schemas import BaseModel

    class Pages(BaseModel):
        pages: list[str]

    r = llm.generate_json("ocr", [llm.user(llm.file_part(data, "application/pdf"),
                                           "Transcribe every page verbatim, one string per page. Do not summarise.")],
                          Pages, "You transcribe documents exactly, preserving numbering and wording.")
    return r.pages


def chunk_text(pages: list[str], max_chars: int = MAX_CHARS) -> list[dict]:
    """Clause-level chunks: a new chunk starts at a numbered heading; long clauses split at sentence boundaries."""
    chunks, cur, sec, page_of = [], [], None, 1

    def flush():
        txt = re.sub(r"[ \t]+", " ", "\n".join(cur)).strip()
        if len(txt) >= 40:
            while len(txt) > max_chars:
                cut = max(txt.rfind(". ", 0, max_chars), txt.rfind("\n", 0, max_chars))
                cut = cut + 1 if cut > max_chars // 3 else max_chars
                chunks.append(dict(section=sec, page=page_of, content=txt[:cut].strip()))
                txt = txt[cut:].strip()
            if txt:
                chunks.append(dict(section=sec, page=page_of, content=txt))
        cur.clear()

    for pno, text in enumerate(pages, 1):
        for ln in text.splitlines():
            m = HEAD.match(ln)
            if m and cur and sum(len(x) for x in cur) > 200:
                flush()
                page_of = pno
            if m:
                sec = m.group(1)
            if not cur:
                page_of = pno
            cur.append(ln)
    flush()
    return chunks


def to_rows(doc_id: str, chunks: list[dict], url: str | None) -> list[dict]:
    meta = MANIFEST[doc_id]
    rows = []
    for n, c in enumerate(chunks, 1):
        rows.append(dict(chunk_id=c.get("chunk_id") or f"{doc_id}-{n:04d}", doc_id=doc_id, doc_type=c.get("doc_type", meta["doc_type"]),
                         policy_id=meta.get("policy_id"), title=meta["title"], issuer=meta["issuer"], ref_no=meta["ref_no"],
                         doc_date=meta.get("doc_date"), status=meta["status"], section=c.get("section"), page=c.get("page"),
                         list_no=c.get("list_no"), url=url, content=c["content"]))
    return rows


def upsert(rows: list[dict]) -> int:
    vecs = llm.embed([f"{r['title']} | {r.get('section') or ''}\n{r['content']}" for r in rows], "document")
    for r, v in zip(rows, vecs):
        r["embedding"] = v
    for i in range(0, len(rows), 100):
        db.insert("corpus_chunks", rows[i:i + 100], upsert_on="chunk_id", timeout=60)
    return len(rows)
