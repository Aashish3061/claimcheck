# Build prompt for Claude Code: ClaimCheck

> Paste everything below this line into Claude Code, run from an empty repo folder that contains this kit (`corpus/`, `sample_claims/`, `eval_seed/`, `make_samples.py`). Start in **plan mode**, approve the plan, then build one milestone at a time.

---

## 0. Your role and how to work

You are the lead engineer building **ClaimCheck**, a deployed AI web app for a graded MBA GenAI project. Four rules decide the grade:
- the product must **work live** on a public URL;
- AI must do real, user-facing work: RAG on our own data, a multi-step workflow, tool use or MCP, and a prompt pipeline we tested and improved;
- the architecture diagram must **match the code**;
- **cost must be measured** per session and projected to 10,000 users.

**Working rules (all mandatory):**
1. **Plan first.** Write the plan, then build milestone by milestone (§12). At the end of each milestone, run its tests, commit, and report: what works, what failed, and the gate result. Stop at every gate and wait for my go-ahead.
2. **AI never decides money.** Every rupee shown to the user comes from the deterministic rules engine (`claimcheck/rules/`). No LLM output is ever parsed into an amount that reaches the user.
3. **Never invent policy or regulatory text.** Quotes shown to users must be **verbatim substrings of chunks stored in Supabase**. If a quote fails that check, the finding's verdict is downgraded (§6).
4. **Gemini settings.** Do **not** send `temperature`, `top_p` or `top_k`. Google deprecated them on 21 Jul 2026 (Gemini API changelog). Control output with system instructions, JSON schemas with enums, validation and a retry instead.
5. **Secrets.** Read keys only from environment variables. Never write a key into code, tests, logs, fixtures or git history. `.env` goes in `.gitignore`. Ship `.env.example` with placeholders only.
6. **Privacy.** Uploaded documents and personal fields are processed in memory and never stored or logged. Logs hold only tokens, latency, cost, stage, model, version and verdict counts.
7. **Use only these user-facing words.** For verdicts before submission: "At risk", "Review", "Payable". For verdicts after settlement: "Potential inconsistency", "Review", "Supported". Never write "wrongly deducted". Every result screen shows: *"An estimate, not a guarantee or legal advice."*
8. **Human checks.** Anything a person must verify (policy clauses, list items, form fields) is marked `TODO(HUMAN)` and listed in `docs/human_checks.md`. Do not mark it done yourself.
9. **If a library or API call fails** because its signature changed, look up the current docs; don't guess. Each API's docs URL is listed in §2.

---

## 1. The product: one engine, four moments

ClaimCheck helps an Indian health-insurance policyholder file a **reimbursement claim**:

1. **Check.** The user uploads documents (final bill, discharge summary, pharmacy bill, prescriptions, investigation reports, tariff card). ClaimCheck classifies and extracts them, the user confirms the extraction, and then:
   - completeness is checked against the insurer's checklist;
   - consistency is checked across documents: name, admission and discharge dates, bill total against the line items, and a prescription for every pharmacy bill;
   - the submission deadline is checked.
2. **Estimate.** For every line item, RAG with function calling finds the governing policy clause and assigns a rule type. The rules engine then computes:
   - the estimated payable amount;
   - the amount at risk;
   - each item's formula and evidence chain.

   A **what-if slider** recomputes the amount at risk for different room rents per day. It uses no LLM call.
3. **Pack.** A PDF containing a cover letter, a document index, the IRDAI standard claim form Part A pre-filled, and a list of exceptions to fix. The browser merges this PDF with the user's original files.
4. **Audit (after settlement).** The user types in the amount the insurer paid per head and the key dates. ClaimCheck then:
   - compares the payment with its estimate and gives a verdict per head;
   - checks the 15-day settlement rule and calculates indicative interest;
   - drafts a grievance letter, only after the user has reviewed and selected the findings.

**In scope:** the 5 fixed policies in `corpus/policy_profiles.json`, chosen from a dropdown. Rule types:
- `PROPORTIONATE_DEDUCTION`
- `ROOM_RENT_CAP`
- `NON_PAYABLE_LIST_I`
- `SUBSUMED_LIST_II_IV`
- `COPAY`
- `DEDUCTIBLE`
- `UNKNOWN`

The final 3–5 active rule types are set in `config.ACTIVE_RULE_TYPES` after the Day-2 data review. Inactive types map to `UNKNOWN`, which gives a "Review" verdict.

**Out of scope:** uploading any policy, cashless pre-authorisation, submitting to insurer portals, Ollama, Hindi, sub-limits, "reasonable and customary" charges.

---

## 2. Stack and pinned facts (verified 7 Oct 2026)

| Area | Choice and facts |
|---|---|
| Runtime | Python 3.12. FastAPI app exported as `app` from `api/index.py`, static frontend in `public/`, hosted on Vercel. Docs: https://vercel.com/docs/functions/runtimes/python. If Vercel's FastAPI preset detects the app differently, follow the docs and keep the routes the same. |
| Vercel limits | Request/response body **4.5 MB**. Hobby plan with Fluid compute: function `maxDuration` up to **300 s**; set `"functions": {"api/index.py": {"maxDuration": 120}}` in `vercel.json`. Python bundle up to 500 MB. |
| Gemini SDK | `google-genai` (≥ 2.28), using `client.models.generate_content`. Docs: https://ai.google.dev/gemini-api/docs. Structured output: `response_mime_type="application/json"` plus `response_json_schema=Model.model_json_schema()`, then validate with Pydantic v2. String enums via `Literal`. |
| Models (in `config.py`, never hard-coded elsewhere) | `EXTRACT_MODEL = REASON_MODEL = GENERATE_MODEL = "gemini-3.5-flash-lite"`; `BENCH_MODEL = "gemini-3.6-flash"`; `EMBED_MODEL = "gemini-embedding-2"`, `EMBED_DIM = 768`. |
| Thinking | `types.ThinkingConfig(thinking_level=...)`, set per stage in config. Flash-Lite defaults to `"minimal"`; allowed values are minimal, low, medium and high. Thinking can't be fully disabled, and thinking tokens are billed as output. |
| PDF and image input | `types.Part.from_bytes(data=..., mime_type="application/pdf"|"image/jpeg"|"image/png")`. Inline limit is 50 MB for PDFs, but **our Vercel cap of 4.5 MB per request decides**: upload one document per request. |
| Function calling | Manual loop with `automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)`, at most 4 rounds, logging `usage_metadata` every round. |
| Usage fields | `prompt_token_count`, `candidates_token_count`, `thoughts_token_count`, `cached_content_token_count`, `tool_use_prompt_token_count`, `total_token_count`. Treat missing fields as 0. |
| Embeddings | `client.models.embed_content(model="gemini-embedding-2", contents=..., config=types.EmbedContentConfig(output_dimensionality=768))`. **No `task_type`.** Put the task in the text, e.g. queries as `"task: search result | query: {q}"`; format documents as the embeddings docs recommend. Vectors come back normalised, so use inner product. Max 8,192 input tokens. |
| Supabase | Postgres with pgvector and full-text search, following the official hybrid-search pattern (https://supabase.com/docs/guides/ai/hybrid-search). Call it over **REST with httpx** (`/rest/v1/...`, RPC at `/rest/v1/rpc/hybrid_search`). Auth headers: `apikey: <SUPABASE_SECRET_KEY>`. Add `Authorization: Bearer <key>` **only** if the key starts with `eyJ` (legacy JWT). The `sb_secret_` key bypasses RLS and is server-only. |
| PDF | `pypdf` 6.x for merging, reading and filling forms (`update_page_form_field_values(..., auto_regenerate=False)`) and `reportlab` for generated pages, on the server. `pdf-lib` in the browser merges the server PDF with the user's originals. |
| MCP | `fastmcp` 4.x, Python ≥ 3.10: `from fastmcp import FastMCP`, `@mcp.tool`, `mcp.run()` (stdio). Inspector: `npx @modelcontextprotocol/inspector`, which needs Node ≥ 22.19. |
| Frontend | A single `public/index.html` with vanilla JS and **no build step**. Chart.js and pdf-lib load from cdnjs or jsdelivr. |
| Tests | pytest. Gemini is mocked with recorded fixtures in unit tests; live tests run behind the `--live` flag. |

**Prices** go in `config.PRICES` with effective dates, in USD per 1M tokens. Exchange rate: `USD_INR = 96.1446` (2 Oct 2026).

| Model | Input | Output (incl. thinking) | Notes |
|---|---|---|---|
| gemini-3.5-flash-lite | 0.30 | 2.50 | no context caching |
| gemini-3.6-flash | 0.75 until 2026-12-31, then 1.50 | 3.75, then 7.50 | caching 0.075, then 0.15 per 1M; storage 0.50, then 1.00 per 1M per hour |
| gemini-3.5-flash | 1.50 | 9.00 | |
| gemini-embedding-2 | 0.20 (text) | – | batch 0.10 |

Source: https://ai.google.dev/gemini-api/docs/pricing. Add a test that fails if any model in use has no price entry.

---

## 3. Repository layout

```
api/index.py              FastAPI app: routes only, thin
claimcheck/
  config.py               models, thinking levels, prices, USD_INR, ACTIVE_RULE_TYPES, caps
  schemas.py              Pydantic models (all LLM I/O + API I/O)
  llm.py                  Gemini wrapper: generate_json(), embed(), function-call loop, usage → cost, retry
  extract.py              classify + extract one document
  checks.py               check_completeness(), check_consistency(), check_deadline()
  rag.py                  embed_query(), hybrid_search(), retrieve_policy_clause(), retrieve_regulatory_rule(), find_non_payable_item()
  reason.py               function-calling agent → rule assignments per line item
  evidence.py             verbatim quote check, number guard
  rules/engine.py         estimate_settlement(), simulate_whatif(), audit_settlement(), settlement_timeline()
  rules/profiles.py       load + validate corpus/policy_profiles.json
  generate.py             explanations, cover letter, grievance letter (with template fallbacks)
  pack.py                 build_pack_pdf(): cover, index, Part A form, exceptions
  logs.py                 write runs rows (no content), daily cap
mcp_server/server.py      FastMCP server exposing the tools
scripts/                  ingest.py, ocr_pdf.py, smoke_live.py, cost_report.py, make_zip.sh, secret_scan.sh
eval/                     cases/, split.json, run.py, ablation.py, bench_models.py, report.py, wilson.py
public/index.html
schema.sql  vercel.json  requirements.txt  .env.example  README.md
docs/architecture.mmd (+ rendered .svg/.png)  docs/human_checks.md  docs/cost.md  docs/eval_report.md
tests/
```

---

## 4. Database (`schema.sql`)

1. `create extension if not exists vector with schema extensions;`
2. `corpus_chunks`, with columns:
   - `id bigserial pk`, `chunk_id text unique`, `doc_id text`;
   - `doc_type text check in ('regulation','policy_wording','checklist','non_payable_item','claim_form')`;
   - `policy_id text null`, `title text`, `issuer text`, `ref_no text`, `doc_date date`;
   - `status text check in ('in_force','repealed','policy_wording','checklist','verify')`;
   - `section text`, `page int`, `list_no int null`, `url text`, `content text not null`;
   - `fts tsvector generated always as (to_tsvector('english', content)) stored`;
   - `embedding extensions.vector(768)`.

   Indexes: GIN on `fts`, HNSW on `embedding vector_ip_ops`, and btree on `(doc_type, policy_id)`.
3. `hybrid_search(query_text text, query_embedding extensions.vector(768), match_count int, filter_doc_types text[], filter_policy_id text default null, full_text_weight float default 1, semantic_weight float default 1, rrf_k int default 50)`. Adapt the Supabase docs function: apply the filters to **both** CTEs, combine with reciprocal rank fusion `1.0/(rrf_k+rank)`, and return the chunk columns plus the score.
4. `runs`, one row per LLM call or stage:
   - `id`, `created_at`, `session_id uuid`, `stage text`, `pipeline_version text`, `model text`, `thinking_level text`;
   - `prompt_tokens`, `output_tokens`, `thoughts_tokens`, `cached_tokens`, `tool_prompt_tokens`;
   - `latency_ms`, `cost_inr numeric`, `ok bool`, `error_code text`, `verdict_counts jsonb`.
   - **No content columns.**
5. `eval_runs`: `id, created_at, pipeline_version, model, thinking_level, split, case_id, metrics jsonb, cost_inr, latency_ms`.
6. `daily_usage(day date pk, sessions int)`, plus an RPC `bump_usage(cap int) returns bool` that increments the count and returns false once it is over the cap. `config.DAILY_SESSION_CAP = 300`.
7. Enable RLS on **every** table with **no policies**, and `revoke execute` on all functions from `anon, authenticated`. Only the server, using the secret key, can access the database.

---

## 5. RAG ingestion (`scripts/ingest.py`)

- **Inputs.** The PDFs in `corpus/raw/`, which **I download by hand** using `corpus/SOURCES.md`. If a file is missing, print the exact filename and URL and skip it.
- **Text extraction.** Use pypdf. If a page yields fewer than 50 characters it is probably scanned: run `scripts/ocr_pdf.py`, which sends the page to Gemini Flash-Lite as "transcribe verbatim, no summarising" and logs the call as stage `ingest_ocr`. Add the paragraphs listed in SOURCES.md to `docs/human_checks.md`.
- **Chunking.**
  - **Policy wordings:** one chunk per numbered clause or sub-clause. Keep the heading in the content and store the section number.
  - **Regulations:** one chunk per numbered paragraph.
  - **Annexure I of the 2020 standardisation circular:** **one chunk per item**, `doc_type='non_payable_item'`, `list_no` set to 1–4, and the content as the item text exactly as printed. Print the per-list counts. Do not trust prior counts; I will verify.
  - Any other chunk over 1,500 tokens is split at sentence boundaries with an overlap of 1 sentence.
- **Metadata** comes from a manifest dict in `ingest.py` built from SOURCES.md: ref no., date, status, URL and `policy_id`.
- **Embeddings.** Batch the requests and log their cost. The script must be idempotent: upsert on `chunk_id`.
- **Self-checks printed at the end:**
  - chunks per doc;
  - 5 sample retrievals: "room rent proportionate deduction" for each policy, "documents from hospitals", "settled within fifteen days", "attendant charges", "telephone charges";
  - **whether every `non_payable_candidate` item in `sample_claims` exists in the List I chunks.** If one doesn't, report it so the fixture can be fixed.

---

## 6. Pipeline: stages, prompts, schemas

All prompts live in `claimcheck/prompts/*.md` with a version header (`v1`, `v2`, `v3`). Each schema is a Pydantic model; the JSON schema is passed to Gemini and the output re-validated. When validation fails, retry once with the validation error appended. If it fails again, return a typed error so the UI falls back to manual entry. Never crash.

### 6.1 Classify + extract (`POST /api/extract`, one file per request)

**Client side:** images are resized to ≤ 2,000 px on the long edge as JPEG at quality 0.8. PDFs over 4 MB are rejected with a clear message.

**Output: `ExtractedDoc`**
- `doc_type`: one of `final_bill, itemised_bill, discharge_summary, pharmacy_bill, prescription, investigation_report, tariff_card, settlement_letter, id_proof, other`.
- `patient_name`, `hospital_name`, `admission_date`, `discharge_date` (ISO).
- `line_items[]`, each with:
  - `line_id`, `description`, `quantity`, `unit_rate`, `amount` (integer rupees);
  - `category`: one of `room, icu, nursing, medical_practitioner_fees, ot_charges, pharmacy, consumables, implants, medical_devices, diagnostics, non_payable_candidate, other`;
  - `room_days`, set for room and ICU lines.
- `stated_total`.
- `tariff[]`, for tariff cards: `{room_category, rate_per_day}`.
- `notes`, e.g. "charges vary by room category".

**Rules:**
- Do **not** ask the model for confidence. Compute which fields need confirmation in code:
  - line items don't sum to the stated total (tolerance ₹1);
  - a date is missing or unparseable;
  - the category is `other`;
  - the amount is ≤ 0.
- The Screen-1 table highlights those fields, and the user's edits overwrite the extracted values. Each confirmed field is flagged `confirmed=true`.

### 6.2 Checks (`POST /api/checks`, code only)

- **`check_completeness(profile, doc_types)`** uses the checklist in the profile. Required: `final_bill`/`itemised_bill`, `discharge_summary`, a `prescription` if a `pharmacy_bill` is present, and `investigation_report` if diagnostics were billed.
- **`check_consistency(docs)`** compares:
  - patient names, with a normalised similarity below 0.9 giving "Review";
  - admission and discharge dates, which must match exactly;
  - the bill total against the sum of line items;
  - room days against the date difference.
- **`check_deadline(profile, discharge_date, today)`** uses `submission_deadline_days_from_discharge`. If the profile value is "TO VERIFY", show "Check your policy's deadline".
- **The documents rule.** When `irdai_master_health_2024` para 17(c) is ingested, show it as information with a verbatim quote: insurers and TPAs are required to collect documents from hospitals. Present the checklist as "documents your insurer's claim page asks for".

### 6.3 Retrieve + reason (`POST /api/estimate`, part 1). This is the function-calling agent.

- **Tools** given to Gemini (also exposed via MCP):
  - `retrieve_policy_clause(policy_id, query)`: top 4 chunks of `policy_wording` for that policy.
  - `retrieve_regulatory_rule(query)`: top 4 chunks of `regulation` or `checklist`.
  - `find_non_payable_item(description)`: top 3 `non_payable_item` chunks, each with its `list_no`.
- **System instruction:** "For each confirmed line item, call the tools, then assign exactly one `rule_type` from the enum. Quote the governing text **verbatim** from a returned chunk, giving its `chunk_id`. If no returned chunk governs the item, use `UNKNOWN`. Do not output any amounts."
- **Output: `RuleAssignment[]`**, each with `line_id`, `rule_type`, `policy_chunk_id`, `policy_quote`, `regulatory_chunk_id|null`, `regulatory_quote|null` and `non_payable_list_no|null`.
- **Pipeline versions** (selected by `pipeline_version` in config and by eval flags):
  - **v0 baseline:** one call with all document parts plus the **full policy wording text**, no tools and no engine. The model outputs an estimate and the items at risk in JSON. This simulates a user uploading everything to a general chatbot. It is used **only in evaluation**, never in the UI.
  - **v1:** separate extract and reason prompts, no RAG (the policy wording is truncated into the prompt), with the model's own arithmetic.
  - **v2:** v1 plus schema, enums and 3 few-shot examples from the **dev split only**.
  - **v3 (production):** RAG tools, the rules engine, the evidence check and confidence gating.

### 6.4 Rules engine (`rules/engine.py`): pure functions, no I/O, no LLM imports

**`estimate_settlement(profile, sum_insured, items, assignments, eligible_room_rent_per_day, room_rent_per_day)`**

1. **Ratio.** `ratio = 1` if the policy has no limit or the actual rent is ≤ the eligible rent; otherwise `eligible / actual`.
2. **Associated expenses.** For each item whose category is in `profile.associated_expense_heads` and **not** in `never_proportionate`, and whose head is billed by room category (the default is yes; if the bill states otherwise, that head is exempt and gets a "Review" note): payable = `round_half_up(amount × ratio)`.
3. **Non-payable items.** `NON_PAYABLE_LIST_I` items: payable = 0.
4. **Subsumed items.** `SUBSUMED_LIST_II_IV` items are payable only inside the parent head, so a separately billed item is "At risk" and marked "Review".
5. **Co-pay, deductible and sum-insured cap,** applied in the order given in the profile.
6. **Output.** For each item: `amount, payable, at_risk, rule_type, formula_text`, with the numbers filled in. The function also returns the totals and `ratio`.

**Other functions:**
- **`simulate_whatif(...)`** takes a `room_rent_values[]` list and reuses the stored assignments, with no LLM call. For each value it returns `payable`, `at_risk_total`, and `at_risk_room_related` (proportionate deduction plus room cap only; non-payable items excluded), holding every other charge constant; the UI says so. The slider plots `at_risk_room_related`. `expected.json` stores that series as `whatif_room_related_at_risk`.
- **`audit_settlement(estimate, per_head_paid)`** returns the variance for each head and a verdict.
- **`settlement_timeline(intimation_date, submission_date, settlement_date, bank_rate)`**:
  - flags settlements that took more than 15 days from submission;
  - computes indicative interest = `paid × (bank_rate + 0.02) × days(intimation → settlement) / 365`;
  - the bank rate is **entered by the user**, with a link to RBI. **Never hard-code it.**
  - The result is labelled "indicative" and cites the in-force PPHI 2024 chunk.

**Confidence and verdicts.** Confidence is `high` only if all three hold:
1. the amounts were confirmed by the user;
2. the evidence check passed for the policy quote;
3. the `rule_type` is not `UNKNOWN`.

| Stage | Verdict | Condition |
|---|---|---|
| Before submission | **At risk** | `at_risk > 0` and confidence is high |
| Before submission | **Review** | confidence is not high |
| Before submission | **Payable** | otherwise |
| After settlement | **Supported** | the variance is within `config.TOLERANCE_INR` (initially 10, tuned on dev) |
| After settlement | **Potential inconsistency** | the variance is over tolerance and confidence is high |
| After settlement | **Review** | otherwise |

**Citation rules.** Only `policy_wording` and `in_force` chunks can support "At risk" or "Potential inconsistency". `repealed` chunks are shown as "Background (repealed 29 May 2024; the rule now sits in your policy wording)".

### 6.5 Evidence and number guards (`evidence.py`)

- **Quote check.** After collapsing whitespace, normalising quotes and dashes, and lower-casing, the quote must be a **substring** of the stored chunk content. If it isn't, the finding falls to "Review" and the event is logged.
- **Number guard for all generated text.** Extract every number from the text. Each must be in the set of numbers present in the findings JSON (formatting-insensitive, so 1,20,000 = 120000). If any isn't, regenerate once; if it still fails, use the deterministic template text. Log `unsupported_number` events; these feed the unsupported-claim metric.

### 6.6 Generate (`generate.py`)

**Inputs:** the findings JSON only.

**Outputs:**
- a 1–2 sentence explanation for each finding, in plain English;
- a cover letter for the claim pack;
- a grievance letter, built from the findings the user ticked.

**Rules:**
- The system instruction forbids new facts and numbers and requires the user-facing words listed in §0.
- Every output has a deterministic template fallback.
- The grievance letter cites the clauses verbatim and leaves the user to sign. It is never sent automatically.

### 6.7 Pack (`POST /api/pack`)

The server returns one PDF of at most 2 MB with these pages:
1. a cover letter;
2. a document index, in checklist order, with present/missing marks;
3. the **IRDAI standard claim form, Part A**, rebuilt with reportlab. Take the field list from Annexure 30 of `irdai_tpa_master_2020` and record it as `TODO(HUMAN)` until checked. Fill it from the personal fields the user typed, plus the extracted dates and amounts;
4. an exceptions list.

Footer on every page: "Prepared with ClaimCheck – check your insurer's own claim form requirements."

The browser then merges it with the user's original files using pdf-lib, embedding images as pages, and offers the download. **Personal fields are never logged.**

---

## 7. API routes (all JSON; the session ID comes from the `X-Session-Id` header)

| Route | Calls an LLM? | Notes |
|---|---|---|
| `POST /api/extract` | yes | One file per call. Increments `daily_usage` on the first call of a session; returns 429 with a friendly message when over the cap. |
| `POST /api/checks` | no | |
| `POST /api/estimate` | yes | Retrieve and reason, then the engine, evidence check and explanations. Returns findings, assignments and totals. |
| `POST /api/whatif` | **no** | The client sends back the assignments. Must answer in under 300 ms server time. |
| `POST /api/pack` | yes (cover letter) | Returns `application/pdf`. |
| `POST /api/audit` | yes (letter only) | |
| `GET /api/health` | no | Returns the model IDs, pipeline version and DB reachability. **No secrets.** |

---

## 8. Frontend (`public/index.html`)

Four screens: tabs or a stepper, mobile-friendly, keyboard accessible, with colour plus text labels.

1. **Upload and confirm.**
   - A policy dropdown filled from the 5 profiles, plus sum-insured and age inputs.
   - Drag-and-drop for multiple files, uploaded in parallel with one request each.
   - Detected document types, a completeness checklist, consistency warnings and the deadline.
   - An editable table of line items with flagged cells highlighted. The user must confirm before continuing.
   - For category-based policies, an input for the eligible room rent, pre-filled from the tariff card if one was uploaded.
2. **Estimate.**
   - Large figures for payable and at-risk.
   - A finding card per item showing the verdict (At risk / Review / Payable) and a "Show calculation" toggle (formula plus evidence chain: policy quote with section, IRDAI quote with ref and status, then the numbers).
   - **The what-if slider:** a Chart.js line chart of at-risk amount against room rent per day, with the eligible cap marked and the current value shown. Requests are debounced.
3. **Pack.** Personal fields (stay in the browser except during the pack call), the exceptions list, the cover letter preview, and "Download claim pack".
4. **After settlement** (a tab). Inputs for the amount paid per head (pre-listed), the intimation, submission and settlement dates, and the bank rate (with a link to RBI). Shows verdicts and the timeline result. The user ticks findings, then generates the grievance letter.

**Also include:**
- A banner on every result screen: *"An estimate, not a guarantee or legal advice."*
- A sample-data button that loads `sample_claims/S1` (shown as "Sample data – synthetic").
- **Replay mode:** `?replay=1` loads recorded API responses from `public/replay/*.json` and shows a red "REPLAY – recorded run" banner. This is the last resort for the demo.
- A small footer: model, pipeline version, and ₹ cost of this session, from the response headers `X-Cost-INR` and `X-Tokens`.

---

## 9. MCP server (`mcp_server/server.py`)

- Built with `FastMCP("ClaimCheck")`. It exposes `retrieve_policy_clause`, `retrieve_regulatory_rule`, `find_non_payable_item`, `check_completeness`, `estimate_settlement`, `simulate_whatif` and `settlement_timeline` by **importing the same functions** as the app, so there is no duplicated logic.
- It runs over stdio. The README shows how to:
  - run it under the Inspector (`npx @modelcontextprotocol/inspector python mcp_server/server.py`);
  - connect it to Claude Desktop (config snippet).
- Optional script `scripts/mcp_gemini_demo.py`: pass the MCP `ClientSession` as `tools=[session]` to `client.aio.models.generate_content`. This Google feature is experimental and supports tools only, so it is **never on the production path**.

---

## 10. Evaluation (`eval/`)

**Cases.** `eval/cases/*.json` covers:
1. the synthetic packs S1–S3 (copied from `sample_claims/expected.json`);
2. the Ombudsman award cases converted from `eval_seed/award_cases_seed.json`. Use only cases where `verified=true`, and use each case's own `terms_profile`, because older awards fall under older rules;
3. the team's real anonymised packs, added later.

**Split.** `eval/split.json` is about 60/20/20 dev/val/test, with a seed and a SHA-256 of the case list, frozen at the gate in M2. The test split runs only with `--final`, which writes `eval/.test_lock`; a second run refuses without `--force --reason "..."`.

**Scripts:**
- `run.py --version v0|v1|v2|v3 --split dev|val|test --model ... --thinking ...` writes `eval_runs` and appends to `docs/eval_report.md`.
- **Metrics:**
  - **Extraction accuracy per field:** synthetic PDFs plus the real packs.
  - **Deduction backtest recall:** of the heads the insurer disallowed, the share flagged At risk or Review.
  - **Precision of At risk / Potential inconsistency flags,** per finding, with a **Wilson 95% CI** (`wilson.py`, with a unit test).
  - **Estimate error:** absolute ₹ error, with median and P90.
  - **Agreement with the Ombudsman, per head.**
  - **Citation validity:** automatic substring check, plus a CSV for manual spot checks.
  - **Unsupported-claim rate:** `unsupported_number` events per generated statement, plus a manual-audit CSV.
- `ablation.py`:
  - for each complete pack, removes each document type in turn and checks it is detected (completeness recall);
  - injects mismatched names, dates and totals and checks they are caught;
  - measures false alarms on the untouched packs.
- `bench_models.py`: v3 on val with Flash-Lite against 3.6 Flash, at thinking levels minimal and low. It reports accuracy, precision, ₹ (median and P90) and latency (median and P90) as a table for slide 8.
- `report.py`: builds `docs/eval_report.md` with the v0→v3 table, the confidence intervals, and a "What failed" section that lists every miss automatically.

---

## 11. Cost, architecture and submission artefacts

- **`scripts/cost_report.py`.** Reads `runs`, groups by `session_id`, and reports median and P90 tokens and ₹ per session, both overall and by stage. Projects to 10,000 users at 0.2, 1 and 3 sessions per user per month, using prices for the current period **and** from 2027-01-01. Fixed infrastructure is an input. Writes `docs/cost.md` for slide 9, including "what changes at scale":
  - Flash-Lite has no context caching, so shrink prompts with retrieval;
  - use caching only if a stage moves to Flash;
  - use the Batch API (50% off) for evaluation runs and re-embedding;
  - route only low-confidence items to the stronger model;
  - add paid tiers and a human-review queue.
- **`docs/architecture.mmd`.** A Mermaid diagram generated from the real routes and functions (input → the 7 stages → tools/DB → output, with AI steps and code steps styled differently, and MCP as a side box). Render it to SVG/PNG with `npx @mermaid-js/mermaid-cli`. Add a test that fails if a route named in the diagram doesn't exist.
- **`scripts/smoke_live.py <URL>`.** Runs S1 end to end against the deployed app and asserts:
  - payable 135,125, at risk 58,875;
  - what-if at 6,000 → `at_risk_room_related` 23,500;
  - audit variance 15,750.
- **`scripts/secret_scan.sh`.** Greps the working tree **and** `git log -p` for `AIza`, `sb_secret_`, `eyJ` and `service_role`. Exits non-zero on any match.
- **`scripts/make_zip.sh`.** Runs the secret scan, then zips the repo to `claimcheck_submission.zip`, excluding `.env*` (except `.env.example`), `.vercel`, `node_modules`, `__pycache__` and `corpus/raw` (the README explains how to fetch the sources).
- **`README.md`** covers:
  - what it is;
  - **where to put keys** (`.env` locally or Vercel environment variables: `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`);
  - Supabase setup (run `schema.sql`);
  - running ingestion;
  - running locally (`uvicorn api.index:app --reload`, or `vercel dev`);
  - tests, evaluation, the cost report and the MCP server;
  - the live URL;
  - known limitations and failures.

---

## 12. Milestones (stop at each gate and report)

| # | Build | Acceptance |
|---|---|---|
| M1 | Skeleton: repo, config, schema.sql, `/api/health`, Vercel deploy, `.env.example`, secret scan | Live URL returns health. Secret scan passes. |
| M2 | Rules engine and profiles, with tests from `sample_claims/expected.json`. Freeze `eval/split.json`. | **Exact match** on S1–S3: totals, every item, what-if points, audit variance 15,750, interest 847 at the test bank rate of 5%. Property tests: `at_risk_room_related` is 0 at or below the cap and never falls as rent rises; `at_risk_total` at the actual rent equals the estimate's at-risk total. **GATE A/B: report usable award cases (need ≥ 15) and the share with enough pre-settlement detail (≥ 70%).** |
| M3 | Extract, the confirm screen, checks | S2 produces all 3 expected check findings. **GATE C: per-field extraction ≥ 90% on the synthetic plus available real packs.** |
| M4 | Ingestion and hybrid search | The self-checks in §5 pass. Every fixture non-payable item is found in the List I chunks (or the fixture is fixed). |
| M5 | Reason agent, then estimate end to end, plus the what-if UI | S1 live: payable 135,125, at risk 58,875, the slider works, and each At-risk finding has a verified policy quote. |
| M6 | Generate, pack, audit tab, evidence and number guards | The pack PDF opens, the browser merge works, and the S1 audit shows 2 Potential-inconsistency findings totalling 15,750. |
| M7 | Evaluation v0–v3, ablation, model benchmark, one run on the test set | **GATE D: At-risk precision ≥ 80% (with CI). GATE E: citation validity ≥ 95%. GATE F: v3 beats v0 on backtest recall or estimate error.** If F fails, report it honestly; don't tune on test. |
| M8 | UI polish, cost logging, reliability (bad scans, a 4.5 MB file, timeouts, cold start), MCP server, architecture diagram | `cost_report.py` produces `docs/cost.md`. The Inspector lists the tools. The diagram test passes. |
| M9 | Freeze: 20–30 logged live runs, replay JSON recorded, README, zip | `smoke_live.py` passes on production, `make_zip.sh` produces a clean zip, and the secret scan passes. |

**If gate A or B fails**, switch to the fallback "Explain my claim": keep checks, evidence and pack; hide the rupee estimate and slider behind a feature flag.

---

## 13. Done means

- [ ] Live URL works end to end on S1; the slider and pack download work.
- [ ] The diagram matches the routes (the test passes).
- [ ] `docs/eval_report.md` covers v0→v3 with CIs and includes a "What failed" section.
- [ ] `docs/cost.md` gives tokens and ₹ per session (median and P90), the 10,000-user projections, and the changes at scale.
- [ ] Model choice is justified by `bench_models.py` output.
- [ ] The MCP server is demonstrable in Inspector.
- [ ] No secrets in the repo or history. The README says where keys go. The zip is built.
- [ ] `docs/human_checks.md` lists every item still to verify.
