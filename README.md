# ClaimCheck

**Get your health-insurance reimbursement claim right before you submit it, then check the insurer's maths afterwards.**

Live app: https://claimcheck-pi.vercel.app (GenAI Startup Sprint, group project)

ClaimCheck reads your hospital documents, checks them for completeness and consistency, finds the clause in your policy wording that governs each bill line, and estimates the payable amount and the amount at risk. A what-if slider shows how the room you chose changed the deductions. ClaimCheck then builds a claim pack and, after settlement, compares what the insurer paid with the estimate.

> AI interprets, code calculates, retrieval substantiates. No LLM ever produces a rupee amount. *An estimate, not a guarantee or legal advice.*

## How it works (see `docs/architecture.mmd`)

| # | Stage | How | Where |
|---|---|---|---|
| 1 | Classify and extract each document | Gemini 3.5 Flash-Lite reads the PDF or image and returns JSON that matches a schema. Arithmetic checks flag fields the user must confirm. | `claimcheck/extract.py` |
| 2 | Checks | Code checks completeness against the insurer's checklist, consistency across documents (name, dates, totals, prescription for pharmacy) and the submission deadline. | `claimcheck/checks.py` |
| 3 | Retrieve (RAG) | Hybrid search over 5 policy wordings, IRDAI circulars and Annexure I items. Postgres full-text and pgvector results are merged by reciprocal rank fusion (Supabase). | `claimcheck/rag.py`, `schema.sql` |
| 4 | Reason (agent) | Gemini function calling with `retrieve_policy_clause`, `retrieve_regulatory_rule` and `find_non_payable_item`. The model assigns a rule type and copies a verbatim quote for each line. | `claimcheck/reason.py` |
| 5 | Evidence check | Each quote must be a substring of the stored chunk. If it isn't, the line's verdict drops to *Review*. | `claimcheck/evidence.py` |
| 6 | Rules engine | Deterministic payable, at-risk and formula per line: proportionate deduction, room cap, non-payable items, co-pay, deductible. | `claimcheck/rules/engine.py` |
| 7 | Generate | Plain-English explanations and letters. A number guard rejects any figure that isn't in the input; template fallback. | `claimcheck/generate.py` |
| 8 | What-if, pack, audit | Room-rent slider (code only), claim-pack PDF (the browser merges it with your originals), settlement audit with the IRDAI 15-day rule. | `app.py`, `claimcheck/pack.py` |

**AI techniques used:** RAG on our own corpus, a multi-step workflow, tool use via native function calling plus an MCP server (bonus), and a prompt pipeline we tested and improved. Versions run from v0 (everything in one prompt, the same as uploading to a chatbot) to v3 (production). Results are in `docs/eval_report.md`.

## Where to put the keys

Never commit keys. Set them in **Vercel → Project → Settings → Environment Variables**. For local runs, copy `.env.example` to `.env`.

| Variable | Value |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SECRET_KEY` | Supabase **secret** key (`sb_secret_...`), used server-side only |
| `ADMIN_ENABLED` | `1` only while ingesting or evaluating; otherwise unset |

## Run it yourself

1. **Supabase:** create a project, then run `schema.sql` in the SQL editor. This creates the tables and the hybrid-search function, turns on RLS and grants access only to the service role.
2. **Deploy:** import the repo in Vercel (it detects the FastAPI preset from `app.py`) and add the environment variables above. Locally, run `pip install -r requirements.txt` followed by `uvicorn app:app --reload` (or `vercel dev`), then open `/index.html`.
3. **Load the corpus:** set `ADMIN_ENABLED=1`, then call `POST /api/admin/ingest_url?doc_id=<id>&url=<pdf url>` for each document in `corpus/SOURCES.md`. Use `POST /api/admin/ingest_pdf?doc_id=<id>` with the PDF as the request body for sites that block servers. Document IDs are listed in `claimcheck/ingest.py`.
4. **Tests:** `pytest -q`. The engine reproduces `sample_claims/expected.json` exactly. The suite also covers the checks, the evidence and number guards, the pack PDF, the MCP tools and a check that the architecture diagram matches the code.
5. **Evaluation:** `POST /api/admin/eval_case?case_id=S1&version=v3` for each case in `eval/cases.json` and each version v0–v3, then `GET /api/admin/report`.
6. **Cost:** `GET /api/admin/cost_report?fixed_infra_inr=0` gives tokens and ₹ per session (median and P90) and a projection to 10,000 users.
7. **MCP server (bonus):** `python mcp_server/server.py` runs over stdio. To inspect it: `npx @modelcontextprotocol/inspector python mcp_server/server.py`.
8. **Sample data:** `python scripts/make_samples.py` regenerates the synthetic claim packs. The hospitals and patients are fictional, and every page is stamped SYNTHETIC.

## Models and cost

- **Models:** Gemini 3.5 Flash-Lite for extraction, reasoning and generation; gemini-embedding-2 at 768 dimensions for retrieval. `eval/harness.py` benchmarks Flash-Lite against Gemini 3.6 Flash.
- **Generation settings:** we send no temperature, top_p or top_k, which were deprecated on 21 Jul 2026. Consistent output comes from JSON schemas, enums, validation and a retry.
- **Cost logging:** every call's `usage_metadata` is logged to `runs` along with its ₹ cost; no document content is logged. See `docs/cost.md`.

## Privacy and safety

- Documents are processed in memory and never stored.
- Personal fields are used only to fill the pack PDF.
- Logs contain token counts and costs only.
- Every Supabase table has RLS on and no public policies.
- A daily session cap protects the API budget.

## Limits (honest list)

- **Five fixed policies.** Their profiles are `verified_by_human=false` until the team checks them (`docs/human_checks.md`).
- **Synthetic evaluation data.** The evaluation uses synthetic cases with known ground truth. Ombudsman award cases are seeded in `eval_seed/` but not yet verified.
- **Repealed circulars.** IRDAI's 2020 proportionate-deduction and standardisation circulars were repealed on 29 May 2024. ClaimCheck cites the policy wording as the binding term and shows those circulars only as background.
- **Out of scope:** sub-limits, "reasonable and customary" charges and cashless claims.
