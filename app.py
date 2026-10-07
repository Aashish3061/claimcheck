"""ClaimCheck API (FastAPI on Vercel). Frontend is public/index.html served from the CDN."""
import json, os, time, uuid
from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from claimcheck import config, db, llm
from claimcheck.schemas import AuditIn, ChecksIn, EstimateIn, PackIn, WhatIfIn

app = FastAPI(title="ClaimCheck")
MAX_UPLOAD = 4_000_000


@app.middleware("http")
async def accounting(request: Request, call_next):
    llm.start_request(request.headers.get("x-session-id") or str(uuid.uuid4()), request.headers.get("x-pipeline-version"))
    t0 = time.time()
    resp = await call_next(request)
    a = llm.acc()
    resp.headers["X-Cost-INR"] = f"{a['cost']:.4f}"
    resp.headers["X-Tokens"] = str(a["tokens"])
    resp.headers["X-Server-Ms"] = str(int((time.time() - t0) * 1000))
    llm.flush(a.get("verdict_counts"))
    if request.url.path.startswith("/api/admin") and config.ADMIN_ENABLED:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    import traceback
    from claimcheck.llm import quota_info
    detail = (quota_info(exc) + " | " + traceback.format_exc()[-600:]) if request.url.path.startswith("/api/admin") and config.ADMIN_ENABLED else None
    return JSONResponse({"error": "server_error", "message": f"{type(exc).__name__}", "detail": detail}, status_code=500)


def err(status, code, msg):
    return JSONResponse({"error": code, "message": msg}, status_code=status)


@app.get("/")
def root():
    return RedirectResponse("/index.html")


@app.get("/api/health")
def health():
    ok_db = False
    if db.configured():
        try:
            db.rest("GET", "corpus_chunks", params={"select": "chunk_id", "limit": "1"}, timeout=5)
            ok_db = True
        except Exception:
            pass
    return dict(ok=True, models=config.MODELS, pipeline_version=config.PIPELINE_VERSION, db_reachable=ok_db,
                gemini_key_set=bool(os.getenv("GEMINI_API_KEY")), admin_enabled=config.ADMIN_ENABLED)


@app.get("/api/policies")
def policies():
    from claimcheck.rules.engine import profiles
    return [dict(policy_id=k, insurer=v["insurer"], product=v["product"], uin=v.get("uin"), room_rent=v.get("room_rent"),
                 verified_by_human=v.get("verified_by_human")) for k, v in profiles().items()]


def _cap_ok(new_session: bool) -> bool:
    if not new_session or not db.configured():
        return True
    try:
        return bool(db.rpc("bump_usage", {"cap": config.DAILY_SESSION_CAP}, timeout=5))
    except Exception:
        return True


@app.post("/api/extract")
async def extract(file: UploadFile = File(...), x_session_new: str | None = Header(default=None)):
    from claimcheck.extract import extract_document
    if not _cap_ok(x_session_new == "1"):
        return err(429, "daily_cap", "Today's free demo capacity is used up. Please try again tomorrow.")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        return err(413, "too_large", "File over 4 MB. Please upload a smaller scan or split the PDF.")
    mime = file.content_type or "application/pdf"
    if mime not in ("application/pdf", "image/jpeg", "image/png", "image/webp"):
        return err(415, "unsupported", "Upload a PDF, JPG or PNG.")
    try:
        return extract_document(data, mime)
    except llm.LLMError as e:
        return err(502, "extract_failed", f"Could not read this document automatically ({e}). You can enter the items manually.")


@app.post("/api/checks")
def checks(body: ChecksIn):
    from claimcheck.checks import run_checks
    return run_checks(body.policy_id, [d.model_dump() for d in body.docs], body.has_diagnostics, body.today)


@app.post("/api/estimate")
def estimate(body: EstimateIn):
    from claimcheck import generate, reason
    from claimcheck.rules import engine
    items = [i.model_dump() for i in body.items]
    try:
        r = reason.assign_rules(body.policy_id, items, "rag")
    except Exception as e:
        r = dict(assignments=[], evidence={}, evidence_detail={}, error=f"{type(e).__name__}")
    est = engine.estimate_settlement(body.policy_id, body.sum_insured, items, r["assignments"],
                                     body.eligible_room_rent_per_day, evidence=r["evidence"])
    try:
        expl = generate.explain(est)
    except Exception:
        expl = {}
    for i in est["items"]:
        i["explanation"] = expl.get(i["line_id"])
        a = next((x for x in r["assignments"] if x["line_id"] == i["line_id"]), {})
        i.update({k: a.get(k) for k in ("policy_section", "policy_title", "regulatory_status", "regulatory_ref")})
    counts = {}
    for i in est["items"]:
        counts[i["verdict"]] = counts.get(i["verdict"], 0) + 1
    llm.acc()["verdict_counts"] = counts
    return dict(estimate=est, assignments=r["assignments"], evidence=r["evidence"], reasoning_error=r.get("error"))


@app.post("/api/whatif")
def whatif(body: WhatIfIn):
    from claimcheck.rules import engine
    ev = {a.line_id: True for a in body.assignments}  # evidence only affects verdicts, not amounts
    return engine.simulate_whatif(body.policy_id, body.sum_insured, [i.model_dump() for i in body.items],
                                  [a.model_dump() for a in body.assignments], body.eligible_room_rent_per_day,
                                  body.room_rent_values[:60], ev)


@app.post("/api/pack")
def pack(body: PackIn):
    from claimcheck import generate
    from claimcheck.pack import build_pack_pdf
    letter = generate.cover_letter(body.policy_id, body.estimate, body.checks)
    pdf = build_pack_pdf(body.policy_id, body.estimate, body.checks, body.personal, body.docs_present, letter)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=claimcheck_pack.pdf"})


@app.post("/api/audit")
def audit(body: AuditIn):
    from claimcheck import generate
    from claimcheck.rules import engine
    a = engine.audit_settlement(body.estimate, body.per_head_paid)
    tl = engine.settlement_timeline(body.intimation_date, body.submission_date, body.settlement_date,
                                    a["total_paid"], body.bank_rate)
    out = dict(audit=a, timeline=tl)
    if body.write_letter:
        rows = [r for r in a["rows"] if r["line_id"] in body.selected_line_ids and r.get("variance")]
        out["letter"] = generate.grievance_letter(body.policy_id, rows, tl) if rows else None
    return out


# ---------------- admin (only while ADMIN_ENABLED=1 in Vercel env) ----------------
def _admin_guard():
    return None if config.ADMIN_ENABLED else err(403, "admin_disabled", "Set ADMIN_ENABLED=1 in Vercel to use admin endpoints.")


@app.post("/api/admin/ingest_url")
def admin_ingest_url(doc_id: str, url: str, ocr: bool = False):
    if (g := _admin_guard()):
        return g
    import httpx
    from claimcheck import ingest
    if doc_id not in ingest.MANIFEST:
        return err(400, "unknown_doc", doc_id)
    r = httpx.get(url, timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 ClaimCheck-ingest"})
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        return err(502, "fetch_failed", f"status {r.status_code}, {r.headers.get('content-type')}")
    return _ingest_bytes(doc_id, r.content, url, ocr)


@app.post("/api/admin/ingest_pdf")
async def admin_ingest_pdf(request: Request, doc_id: str, url: str = "", ocr: bool = False, part: int = 0, page_offset: int = 0):
    """part/page_offset let a large PDF be sent as page-range parts (each under Vercel's 4.5 MB body limit)."""
    if (g := _admin_guard()):
        return g
    return _ingest_bytes(doc_id, await request.body(), url or None, ocr, part, page_offset)


def _ingest_bytes(doc_id, data, url, ocr, part=0, page_offset=0):
    from claimcheck import ingest
    pages = ingest.pdf_pages(data)
    chars = sum(len(p) for p in pages)
    if ocr or chars < 200 * max(len(pages), 1) * 0.3:
        pages = ingest.ocr_pdf(data)
    chunks = ingest.chunk_text(pages)
    if doc_id == "irdai_standardisation_2020":
        from claimcheck.annexure import annexure_items
        chunks += annexure_items(pages)
    for c in chunks:
        c["page"] = (c.get("page") or 0) + page_offset
        if part and not c.get("chunk_id"):
            c["part"] = part
    rows = ingest.to_rows(doc_id, chunks, url)
    n = ingest.upsert(rows)
    return dict(doc_id=doc_id, pages=len(pages), chars=chars, chunks=n,
                non_payable_items=sum(1 for r in rows if r["doc_type"] == "non_payable_item"))


@app.post("/api/admin/pdf_text")
async def admin_pdf_text(request: Request, first: int = 1, last: int = 3):
    if (g := _admin_guard()):
        return g
    from claimcheck import ingest
    pages = ingest.pdf_pages(await request.body())
    return dict(n_pages=len(pages), chars=[len(p) for p in pages], pages={i: pages[i - 1] for i in range(first, min(last, len(pages)) + 1)})


@app.get("/api/admin/chunk")
def admin_chunk(id: str):
    if (g := _admin_guard()):
        return g
    from claimcheck import rag
    c = rag.get_chunks([id]).get(id)
    return {k: c.get(k) for k in ("chunk_id", "doc_type", "section", "page", "status", "content")} if c else {}


@app.get("/api/admin/search")
def admin_search(q: str, doc_types: str = "policy_wording", policy_id: str | None = None, k: int = 4):
    if (g := _admin_guard()):
        return g
    from claimcheck import rag
    return [{k2: r.get(k2) for k2 in ("chunk_id", "doc_type", "section", "list_no", "status")} | {"text": r["content"][:300]}
            for r in rag.hybrid(q, doc_types.split(","), policy_id, k)]


@app.post("/api/admin/eval_case")
def admin_eval_case(case_id: str, version: str = "v3", model: str | None = None, thinking: str | None = None,
                    split: str = "dev"):
    if (g := _admin_guard()):
        return g
    from eval.harness import run_case
    llm.acc()["version"] = version
    return run_case(case_id, version, model, thinking, split)


@app.get("/api/admin/report")
def admin_report():
    if (g := _admin_guard()):
        return g
    from eval.harness import build_report
    return Response(build_report(), media_type="text/markdown")


@app.get("/api/admin/cost_report")
def admin_cost_report(fixed_infra_inr: float = 0):
    if (g := _admin_guard()):
        return g
    from scripts.cost_report import build
    return Response(build(fixed_infra_inr), media_type="text/markdown")
