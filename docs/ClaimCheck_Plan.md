# ClaimCheck: ideation, build and presentation plan

**GenAI Startup Sprint (group project).** Version 4.1: the claim pack builder with a what-if slider. Sources verified 7 Oct 2026.

> **Get your reimbursement claim right before you submit it, then check the insurer's maths afterwards.**
> AI reads and interprets the documents, code calculates the money, and retrieval supplies the evidence.

---

## 0. What the brief asks for, and where this plan covers it

| Requirement in the brief | Covered in |
|---|---|
| A real product where AI is a core feature the user sees, not a chatbot wrapper | §2, §4 |
| Working and deployed, with a live URL on the day | §4.1, §8 |
| More than a wrapper: RAG on our own data, a multi-step workflow, tool use or MCP, and a prompt pipeline we tested and improved | §4.2–§4.6 |
| Slide (a): what happens when the user does the main thing | §9, slide 5 |
| Slide (b): the model(s) used and why | §5.1, slide 8 |
| Slide (c): measured tokens and rupees for one typical session | §5.2, slide 9 |
| Slide (d): monthly cost at 10,000 users, and what changes at that scale | §5.3, slide 9 |
| A 4-minute pitch with 2 minutes of Q&A, and at most 10 slides (.pptx or .pdf) | §9 |
| A code zip with no API keys, a README saying where keys go, submitted 2 hours before class | §11 |
| Reward for ambition, real AI use, measured costs and an honest account of failures | §6, §7, slide 7 |

The rubric is out of 30: product 10, AI sophistication 8, architecture and cost 5, presentation 7. The deciding line is *"a simple product that works scores higher than an ambitious one that does not."*

---

## 1. Ideation (four rounds)

### 1.1 Round 1: three different directions

| Direction | Sketch | Desirability | Feasibility | Fit with the rubric | Strength of evidence |
|---|---|---|---|---|---|
| **ClaimCheck** (health insurance) | Audit a partly paid claim against the policy and IRDAI rules | 5 | 3 | 5 | High |
| **NoticeMitra** (GST) | Explain a GST notice, reconcile it, draft the reply | 4 | 3 | 4 | Low (we found no data on MSME pain; missing data was treated as unknown, not as low pain) |
| **AdaptIQ** (EdTech) | Questions that adapt to the student's answers | 3 | 5 | 3 | Medium |

We dropped AdaptIQ: it is the hardest to tell apart from existing tools ("why not NotebookLM?"), and a 10-day sprint can't prove it improves learning.

### 1.2 Rounds 2–3: the two finalists in depth

**ClaimCheck:**
- **Size of the problem:**
  - FY24: about ₹26,000 crore of health claims were disallowed or repudiated, up 19.10%.
  - FY25: 32.6 million claims, ₹94,248 crore paid, repudiation about 8%.
  - Health made up 61.49% of insurance complaints in FY25.
  - The Ombudsman decided 41% of health complaints in the policyholder's favour.
  - LocalCircles survey: 33% of respondents were only partly paid. The 30,366 respondents chose to answer, so this is a signal, not a population estimate.
- **Weakest existing fix:** unexplained deductions on individual line items.
- **Competitors:** fairClaims (free; analyses rejected and short-paid claims) and ClaimSetu (scores B2B group claims before submission).

**NoticeMitra:** ClearTax already covers notice tracking and AI matching of input tax credit, and any demo would rely on synthetic data.

**Scored against the brief's rubric** (the round-2 scores we accepted):

| Idea | Score out of 30 |
|---|---|
| ClaimCheck | 29 |
| NoticeMitra | 26 |
| AdaptIQ | 22 |

These scores only hold if the product works, which is why §7 sets go/no-go gates.

### 1.3 Round 4: feedback on the business case (accepted)

1. **The audit comes too late.** Once the insurer has paid, the money is already lost and the only option is a grievance. The real value is in getting the claim right *before* it is submitted.
2. **An audit alone is easy to copy.** Anyone can upload the documents to a general-purpose AI chat and ask it to check the deductions.

**Our response:** moving earlier doesn't solve point 2 by itself, because a general-purpose AI can also produce a checklist. What it can't easily do is check *your* documents against *your* policy's rules and compute the payout in code, with a citation for each item. So the differentiator is the rules engine with evidence, applied earlier in the journey. We also prove the difference: a general-purpose AI baseline, called v0, is part of the evaluation (§6).

**What we checked:**
- **Reimbursement is a large market.** It was 29.34% of health claim payouts in FY25 (cashless was 66.35%). That is about ₹27,650 crore of the ₹94,248 crore.
- **Gate 0 is resolved, and the at-risk estimate leads.** Para 17(c) of IRDAI/HLT/CIR/PRO/84/5/2024 says: "Insurers and Third Party Administrators (TPAs) shall collect the required documents from the Hospitals. Policyholder shall not be required to submit the documents." Para 15(a) says reimbursement should happen only in exceptional circumstances. Insurers' claim pages still list the documents they want (Star Health: within 15 days of discharge; Niva Bupa: within 30). So completeness checks stay, framed as "what your insurer's page asks for", and ClaimCheck also tells the user about this right.
- **The 2020 rules have been repealed.** The circular banning proportionate deductions on pharmacy, implants, diagnostics and ICU (IRDAI/HLT/REG/CIR/151/06/2020), and the circular with the non-payable lists, were both repealed by the 2024 master circular. The same terms now live in the **policy wordings**: Star FHO, Niva ReAssure 2.0, HDFC Optima Secure and ICICI Elevate all exclude these heads. **So findings cite the policy clause, and the 2020 circulars appear only as labelled background.**
- **A new in-force rule.** Non-cashless claims must be settled within **15 days of submission**, or the insurer owes interest at the bank rate + 2% (IRDAI/PP&GR/CIR/MISC/117/9/2024). The after-settlement audit now checks this.

**Three ways to reshape the product:**

| | A. Claim Pack Builder | B. Admission Advisor + Pack | C. B2B pre-check |
|---|---|---|---|
| Sketch | Check the documents → estimate the payout and the amount at risk → build the claim pack; audit after settlement as the final step | Starts at admission ("choose a room at or below ₹X"), then builds the pack | The same engine sold to HR teams and TPA desks |
| Desirability | 5 | 5 | 3 |
| Feasibility | 4 | 3 (needs tariff data and a second flow) | 3 |
| Fit with the rubric | 5 | 4 | 3 |
| Differentiation | Medium–high | High | Low (ClaimSetu already does this) |

**Decision:** we build **A, plus B's best moment as a what-if slider.**
- The engine is deterministic, so the user can change the room rent and immediately see the at-risk amount change. That shows the deduction could have been avoided.
- B's full admission flow and C stay on the roadmap slide.

---

## 2. The product

**In one line:** ClaimCheck prepares a reimbursement claim that is ready to submit. It finds missing or inconsistent documents, estimates the payout under the policy terms in code, flags the deductions at risk with evidence, and after settlement checks the insurer's figures against that estimate.

**User:** a policyholder (or their family) filing a reimbursement claim after discharge.

**Language rules:**
- We say "at risk" and "potentially inconsistent". We never say "wrongly deducted".
- The disclaimer reads: "An estimate, not a guarantee or legal advice."

### 2.1 The journey: one engine, four moments

1. **Check.** Upload the documents. ClaimCheck sorts them by type, checks completeness against the insurer's checklist, and checks they agree with each other (names, dates, totals; a prescription behind every pharmacy bill).
2. **Estimate.** The rules engine gives the likely payout and the at-risk items, each with a policy clause and an IRDAI citation. The **what-if slider** lets the user change the room rent per day and see the at-risk amount recalculate.
3. **Pack.** An indexed PDF with the claim form pre-filled, a cover letter and a list of things to fix before submitting.
4. **Audit, after settlement.** The user enters the insurer's settlement. ClaimCheck compares it with the estimate, flags gaps (🟢 Supported / 🟡 Review / 🔴 Potential inconsistency) and drafts a grievance letter once the user has reviewed the flags.

### 2.2 Scope

**In:**
- 5 fixed policies, chosen from a dropdown, with their insurers' claim forms and document checklists.
- 3–5 types of deduction, chosen after analysing the cases on Day 2. Likely candidates:
  - proportionate deduction for room rent. IRDAI's 2020 rule says it may not be applied to pharmacy, implants, medical devices, diagnostics or ICU charges.
  - non-payable items under Annexure I of the 2020 standardisation circular, which policy wordings still reference: List I (optional items) and Lists II–IV (folded into room, procedure and treatment charges). We count the items from the PDF ourselves.
  - room-rent cap.
  - co-pay and deductible.
- The what-if slider for room rent.

**Cut, kept for the roadmap:**
- The full admission advisor (B) and the B2B version (C).
- Cashless pre-authorisation.
- Submitting automatically to insurer portals.
- Uploading any policy.
- Ollama.
- A letter in Hindi.
- Sub-limits, and "reasonable and customary" charges.
- Making MCP a dependency (it stays as a bonus; see §4.5).

**Fallback** if gates A or B fail: "Explain my claim". Completeness, the evidence chain and the pack are kept; the rupee estimate is dropped.

### 2.3 Screens

1. **Upload and confirm.** The detected document types, a completeness checklist and an editable table of what was extracted, with uncertain fields highlighted.
2. **Estimate.** The estimated payable and at-risk amounts shown large, a card per finding (🟢 Payable / 🟡 Review / 🔴 At risk) with a "Show calculation" button, and the **what-if slider**: a chart of payable amount against room rent, with the policy cap marked.
3. **Pack.** The exceptions to fix, the cover letter, and a "Download claim pack" button (PDF).
4. **After settlement** (a tab). Enter the amount paid → compare it with the estimate → evidence chain → grievance letter.

---

## 3. Data, by purpose

| Data | Purpose | Source | Notes |
|---|---|---|---|
| IRDAI circulars: proportionate deduction (2020), the non-payable item lists, the master circular (May 2024) | Grounding the rules | IRDAI | Chunked by clause. On Day 1, read the master circular's text on documents. |
| 5 policy wordings | RAG for each policy | Insurer websites | The 5 products that appear most often in the evaluation set |
| Insurer claim forms and document checklists | Rules for completeness checks and form filling | Insurer and TPA websites | Note which forms are fillable PDFs |
| Ombudsman health awards | **Backtest set.** These are adjudicated outcomes, not ground truth. | CIO compilations, e.g. *Health_individual April 2021* | Usable if the award gives the pre-settlement details (room rent, cap, bill heads) and the deductions |
| Real claim packs, anonymised and shared with consent | Robustness tests, and completeness tests where documents are removed | Team members' families and friends | Names and IDs removed before anything enters the repo |
| Demo case | Demo | Rebuilt from one award | Labelled on screen: *"Demo case reconstructed from publicly available Ombudsman award."* Complainant not named. |

**Demo case changed.** The live demo now uses **synthetic case S1**: a fictional hospital and patient, every page stamped SYNTHETIC, under Star Health Family Health Optima terms with a ₹4 lakh sum insured and a ₹5,000/day room cap.
- **The bill:** ₹1,94,000, including a ₹8,000/day room for 4 days.
- **ClaimCheck's estimate:** ₹1,35,125 payable, ₹58,875 at risk.
- **The slider:** room-related risk is ₹55,875 at ₹8,000/day, ₹23,500 at ₹6,000/day, and ₹0 at ₹5,000/day.
- **The settlement:** typed in, not a fake insurer letter. The insurer also pro-rated pharmacy and diagnostics, so ₹15,750 is a potential inconsistency.

The L Ramesh award (claimed ₹3,00,279, paid ₹78,865, Ombudsman awarded ₹34,200) is now **an evaluation case only**. The insurer applied no proportionate deduction, and the award turned on Covid-era GI Council guidance that isn't in our corpus. Its April 2021 PDF also now returns 404, so its figures must be verified before use.

**Split:** label everything and freeze the split on Day 2, before any prompt work: about 60/20/20 (12/4/4 for 20 cases). **We never tune on the test set.** Precision is measured per finding, not per case.

**Privacy:**
- Documents are processed in memory and never stored. The pack is generated per request and returned as a download.
- Personal fields on the claim form (name, policy number) are typed into the browser and are never logged.
- Logs hold only tokens, latency, cost, verdict counts and version.
- No API keys go in the repo.

---

## 4. Build

### 4.1 Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | A single HTML/JS page; Chart.js for the what-if chart | Fewest moving parts during a demo |
| Backend | Python serverless functions on Vercel, with keys in Vercel's environment variables | Live URL; same language as the rules engine and FastMCP |
| LLM | Gemini 3.5 Flash-Lite, benchmarked against Gemini 3.6 Flash | Reads PDFs and images natively, returns JSON to a schema, supports function calling, low cost |
| Embeddings | gemini-embedding-2 at 768 dimensions | $0.20 per 1M text tokens. Vectors come back normalised. |
| Data | Supabase Postgres with pgvector and full-text search; row-level security on, no public policies, accessed only from the server with the secret key | Hybrid retrieval in a single database function |
| Rules engine | Plain Python with unit tests | **No LLM ever produces a rupee figure.** It also makes the slider instant and free. |
| PDF pack | pypdf to merge and fill form fields; reportlab for the cover page, index and text overlay on forms that aren't fillable | Mature libraries that work on Vercel |

**Generation settings:** send **no** temperature, top_p or top_k. They were deprecated on 21 Jul 2026, per the Gemini API changelog. Instead, consistency comes from schemas with enums, the system instruction, validation and one retry. Thinking is set with `thinking_level`; Flash-Lite defaults to minimal, and thinking is billed at the output rate.

**Check on Day 1:** Vercel's request-body limit (we have 4.5 MB in mind; resize images in the browser), the function timeout, and Gemini's rate limits.

### 4.2 Pipeline

```
Policy (dropdown) + documents (bill, discharge summary, prescriptions, reports, receipts)
 │
1 CLASSIFY + EXTRACT [AI]   Flash-Lite, PDF/image → JSON: doc type, line items, dates, names, totals
 │                          → user confirms or edits on Screen 1
2 CHECK [code]              check_completeness(): against the insurer's checklist
 │                          check_consistency(): names, dates, totals, prescription↔pharmacy
3 RETRIEVE [AI + DB]        retrieve_policy_clause(), retrieve_regulatory_rule()
 │                          hybrid: tsvector + pgvector, combined by reciprocal rank fusion (k=60)
4 REASON [AI]               Flash-Lite + function calling → rule_type per line item (enum, or UNKNOWN)
 │                          + chunk IDs + exact quotes
5 ESTIMATE [code]           estimate_settlement() → payable, at risk, per-item formula
 │                          evidence check: each quote must appear word for word in its cited chunk
 │                          simulate_whatif(room_rent) → recalculation, no LLM call
6 GENERATE [AI]             explanation for each finding, cover letter, list of exceptions
7 ASSEMBLE [code]           build_claim_pack() → indexed PDF with the form pre-filled
 ┆ later
8 AUDIT [code + AI]         settlement vs estimate → verdicts → grievance letter (after the user reviews)
```

**Rule types (enum):** `PROPORTIONATE_DEDUCTION`, `NON_PAYABLE_LIST_I`, `SUBSUMED_LIST_II_IV`, `ROOM_RENT_CAP`, `COPAY`, `DEDUCTIBLE`, `UNKNOWN`. The final 3–5 are picked on Day 2.

### 4.3 Rules engine and what-if

**Each finding records:**

```json
{
  "line_item": "Nursing charges",
  "amount": 18000,
  "rule_type": "PROPORTIONATE_DEDUCTION",
  "policy_rule": {"chunk_id": "starA-4.2", "quote": "..."},
  "regulatory_rule": {"chunk_id": "irdai-2020-pd-3", "quote": "..."},
  "formula": "18000 × (1 − 5000/8000)",
  "at_risk": 6750,
  "confidence": "high",
  "verdict": "AT_RISK"
}
```

The values in this example show the format only; they are not case data.

**Formulas:**
- **Proportionate deduction:** at risk = eligible charge × (1 − eligible room rent ÷ actual room rent), only when actual rent exceeds eligible rent. Charges excluded by the policy wording (pharmacy, consumables, implants, devices, diagnostics, ICU) are left out.
- **Lists I–IV:** classify each item against IRDAI's lists and apply the treatment the circular sets for that list. Member D checks the wording against the circular text on Day 2, before any code is written.
- **Co-pay and deductible:** applied in the order the policy wording sets out.

**What-if:** `simulate_whatif(room_rent)` reruns `estimate_settlement` with only the room rent changed.
- The chart samples the full range of room rents in a single call.
- Unit tests:
  - the at-risk amount is 0 at or below the cap;
  - it never decreases as room rent rises;
  - with the original room rent, it matches the main estimate exactly.
- It is labelled: *"Based on this policy's room-rent terms; for your next admission."*

**Verdicts before submission:**
- 🟢 **Payable**
- 🔴 **At risk:** a rule applies, confidence is high and the evidence check passed.
- 🟡 **Review:** anything else, including UNKNOWN and a failed evidence check.

Confidence is high only if all three hold: the amounts were confirmed by the user, the quotes passed the evidence check, and the rule type is not UNKNOWN.

**Verdicts after settlement:**
- 🟢 **Supported:** the variance is within tolerance. Tolerance is set from development data on Day 2, starting at ₹10.
- 🔴 **Potential inconsistency.**
- 🟡 **Review.**

### 4.4 Evidence chain

Each finding links: policy clause (quoted, with its section) → IRDAI provision (quoted, with circular number and date) → calculation (the formula with the numbers in it) → [after settlement] what the insurer paid → variance → confidence and verdict.

### 4.5 Tools and MCP

- **The production path is native Gemini function calling** with `retrieve_policy_clause`, `retrieve_regulatory_rule`, `check_completeness`, `estimate_settlement`, `simulate_whatif` and `build_claim_pack`.
- **Bonus, off the critical path:** a FastMCP server that exposes the same tools.
  - We demonstrate it in MCP Inspector or Claude Desktop, and it appears on the architecture slide.
  - Gemini's support for calling MCP sessions is experimental and covers tools only, so the live product never depends on it.

### 4.6 Prompt pipeline versions (proof that we tested and improved it)

| Version | What it is |
|---|---|
| **v0 baseline** | All documents plus the policy in one Gemini prompt, no tools: what a user gets by uploading everything to a general-purpose AI. **It answers "why not just ChatGPT?" with data.** |
| v1 | Separate extraction and reasoning prompts |
| v2 | Adds the JSON schema, enums and few-shot examples from the development set |
| v3 | Adds RAG, the rules engine, the evidence check and confidence gating |

Each version is scored on the validation set. Only the final version runs once on the test set. v0 runs on the test set too, as the comparison.

---

## 5. Model choice and cost

### 5.1 Model (slide 8)

**We use a proprietary API, not an open model or a hybrid.**
- **Why:** it reads PDFs and images natively, returns schema output, and supports function calling, at the lowest per-token price we found.
- **Why not Ollama:** Vercel has no GPU, and running a model on a laptop during the demo adds risk.
- **Trade-offs:** documents go to a third-party API (handled by not storing anything), and we depend on one vendor.

**Benchmark:** Flash-Lite against 3.6 Flash on the validation set, comparing accuracy per field, precision of at-risk flags, median and 90th-percentile cost, and latency. A stage is routed to Flash only if Flash beats Flash-Lite on that stage with non-overlapping confidence intervals.

### 5.2 Cost per session (measured)

**Prices** (per 1M tokens; USD/INR 96.1446 on 2 Oct 2026):

| Model | Input | Output |
|---|---|---|
| 3.5 Flash-Lite | $0.30 = ₹28.84 | $2.50 = ₹240.36 |
| 3.5 Flash | $1.50 = ₹144.22 | $9.00 = ₹865.30 |
| 3.6 Flash | $0.75 = ₹72.11 until 31 Dec 2026, then $1.50 | $3.75 = ₹360.54, then $7.50 |
| gemini-embedding-2 | $0.20 = ₹19.23 | – |

Thinking tokens are billed at the output rate; confirm this on the pricing page.

**Cost per call (₹)** = [uncached input × input price + cached input × 0.1 × input price + (output + thinking) × output price] ÷ 10⁶. The token counts come from each call's `usageMetadata`. A session is the sum of classify/extract, reason and generate, plus the query embeddings. The what-if slider and pack assembly cost ₹0, because no LLM is called.

**Unit example:** 10,000 input + 2,000 output tokens on Flash-Lite = ₹0.29 + ₹0.48 = ₹0.77.

**Reported:** median and 90th-percentile tokens and ₹ per session across 20 or more logged runs, broken down by stage.

### 5.3 At 10,000 users (slide 9)

**Monthly cost** = users × sessions per user per month × median ₹ per session + fixed infrastructure.

- Claims are episodic, so we show three scenarios: 0.2, 1 and 3 sessions per user per month.
- The 90th percentile gives the high case.
- Fixed costs for Supabase and Vercel are priced on Day 9.

**What changes at scale:**
1. Flash-Lite has **no context caching**, so keep prompts small by retrieving only the top clauses. Use caching (90% off) only if a stage moves to Flash.
2. Route only low-confidence items to the stronger model.
3. Use the Batch API (50% cheaper) for re-running evaluations and re-embedding.
4. Move to paid tiers to get rate-limit headroom.
5. Set up a human review queue for 🟡 items.

---

## 6. Evaluation

| Metric | How it's measured | Target |
|---|---|---|
| Extraction accuracy | Per field (amounts, categories, dates, totals) against hand labels | ≥ 90% |
| **Deduction backtest: recall** | On award cases, using only pre-settlement inputs: the share of the insurer's actual deductions that ClaimCheck flagged 🔴 or 🟡 | Reported, v0 vs v3 |
| Precision of 🔴 flags | Per finding, as a count with a Wilson 95% confidence interval | ≥ 80% |
| Estimate error | Absolute ₹ difference between the estimate and the amount actually paid; agreement with the Ombudsman award reported separately | Reported, v0 vs v3 |
| Completeness detection | Remove one document from a complete pack and check whether it is caught (recall); also measure false alarms on complete packs | Recall ≥ 90% |
| Consistency detection | Inject mismatched names, dates or totals and check whether they are caught | Reported |
| Citation validity | Each quote is found verbatim in its chunk, and a hand check confirms the chunk supports the rule | ≥ 95% |
| Unsupported-claim rate | Share of generated statements that aren't backed by evidence (manual audit of the test set) | < 5% |
| What-if correctness | Unit tests in §4.3 | 100% pass |
| Cost and latency | Median and 90th percentile from the logs | Reported |

Results go in an `eval_runs` table, which feeds slide 7. **Failures are reported honestly.**

---

## 7. Go/no-go gates

| Gate | Day | Pass condition | If it fails |
|---|---|---|---|
| 0 | 1 | ✅ Done (7 Oct): para 17(c) confirmed | The at-risk estimate leads; completeness is secondary |
| A | 2 | ≥ 15 usable cases | Switch to the "Explain my claim" fallback |
| B | 2 | ≥ 70% of cases have enough pre-settlement detail to backtest | Fallback, or narrow to the deduction types that do |
| C | 3 | Extraction ≥ 90% per field | All fields must be confirmed; add few-shot examples |
| D | 7 | 🔴 precision ≥ 80% per finding, with its confidence interval | Raise the threshold, so uncertain 🔴 becomes 🟡 |
| E | 7 | Citation validity ≥ 95% | Re-chunk, tighten the evidence check |
| F | 7 | v3 beats v0 on backtest recall or estimate error | Report it honestly; lead the pitch with the evidence chain and the pack instead |

---

## 8. 10-day plan and owners

| Member | Owns | Demo failure mode they own |
|---|---|---|
| A | Product, pitch, UX, deck | Running over time; Q&A |
| B | Data, labelling, evaluation, v0 baseline | A wrong demo case; the numbers on slide 7 |
| C | Classification and extraction, consistency checks, model benchmark | Extraction errors (the confirm screen is the fix) |
| D | RAG, rules engine, **what-if**, tools, MCP bonus | Retrieval misses; calculation bugs |
| E | Frontend, **pack builder**, Vercel/Supabase, logging, QA | Deployment, timeouts, network; runs the reliability ladder |

| Day | Work | Output |
|---|---|---|
| 1 | Freeze scope; read the circular (gate 0); collect awards, policies, IRDAI text, claim forms and checklists; skeleton deployed; check prices and limits | Corpus collected, skeleton live |
| 2 | Label cases; freeze the split; build and test the rules engine; pick the 3–5 rule types | **Gates A, B** |
| 3 | Classification, extraction, confirm screen, completeness and consistency checks | **Gate C** |
| 4 | Chunking, embeddings, hybrid retrieval, citations | Correct clauses returned on development cases |
| 5 | End-to-end estimate plus the **what-if slider** | First complete run |
| 6 | Pack builder, evidence chain, confidence gating, audit tab | All screens working |
| 7 | Evaluate v0–v3 (backtest, document removal, injection); benchmark the models; one run on the test set | **Gates D, E, F**; slide 7 data |
| 8 | UI polish, cost logging, reliability tests (bad scans, timeouts, cold starts), MCP bonus | Slide 9 data |
| 9 | Freeze; 20–30 logged runs; record the replay; deck, README, zip | Ready to submit |
| 10 | Two timed rehearsals, Q&A drill, pre-flight check | Ready |

**Reliability ladder on the day:**
1. Live run.
2. Live run, fixing the extraction on Screen 1 if needed.
3. A recorded replay, **only** if the infrastructure fails, and we say so out loud.

---

## 9. Presentation

### 9.1 Pitch (4:00)

| Time | Section | Content |
|---|---|---|
| 0:00–0:25 | Problem | "A ₹3 lakh claim was paid ₹78,865, and it took the Ombudsman to recover ₹34,200 more" (a real 2021 award; figures to be verified, otherwise use a verified case). Health is 61.49% of insurance complaints, and ₹27,650 crore a year is paid out as reimbursement. |
| 0:25–0:40 | Solution | "ClaimCheck gets the claim right before you submit it, and checks the insurer's maths afterwards." |
| 0:40–2:40 | **Live demo** | Synthetic case S1: upload → confirm → completeness flag (one document removed beforehand, and we say so) → **₹58,875 at risk** → Show calculation → policy clause → **slide room rent from ₹8,000 to ₹5,000: room-related risk falls from ₹55,875 to ₹0** → download the pack → after settlement: the insurer pro-rated pharmacy and diagnostics → **₹15,750 potential inconsistency**, plus the 15-day interest check |
| 2:40–3:10 | Architecture | Slide 5: AI steps and code steps; "no LLM touches the money" |
| 3:10–3:35 | Evaluation | v0 (general-purpose AI) vs v3 on backtest recall and estimate error; precision with its confidence interval; one honest failure |
| 3:35–3:55 | Cost | ₹ per session (median and 90th percentile), 10,000-user scenarios, what changes at scale |
| 3:55–4:00 | Close | "We don't ask AI to decide the money. AI finds the evidence; code proves the math." |

### 9.2 Deck (at most 10 slides)

1. **Title and hook**
2. **Problem:** the data from §1.2–§1.3, with sources
3. **Solution:** the four moments, with a before/after
4. **Demo:** the live URL, with backup screenshots
5. **Architecture (a):** the pipeline from §4.2 as a diagram, with AI and code steps marked
6. **AI sophistication:** RAG, the multi-step workflow, tool use (MCP bonus), and v0→v3
7. **Evaluation:** metrics with confidence intervals, v0 against v3, what failed
8. **Model choice (b):** the reasoning, the benchmark, the trade-offs
9. **Cost (c), (d):** cost per session by stage, the 10,000-user scenarios, changes at scale
10. **Roadmap and close:** admission advisor (B), B2B (C), limits, closing line

### 9.3 Q&A preparation

| Question | Answer |
|---|---|
| "Why not just ChatGPT?" | We tested exactly that: v0. Show the gap from slide 7. ChatGPT gives a checklist; we compute your payout in code from your policy's rules, cite each item, and build the pack. |
| "IRDAI says insurers collect the documents." | Give the answer from gate 0. In either case the at-risk estimate and the audit still apply. |
| "Room rent is decided at admission, so isn't this too late?" | For this claim it tells you what to expect. The slider shows what to choose next time, and the admission advisor is next on the roadmap. |
| "fairClaims and ClaimSetu exist." | fairClaims works after the claim; ClaimSetu is for B2B group claims. We give individuals a pre-submission estimate with evidence and a ready-to-submit pack. |
| "How do you know it's right?" | The backtest against real outcomes, precision with confidence intervals, a test set we never tuned on, and every rupee coming from tested code. |
| "Hallucinated clauses?" | Every quote must appear word for word in its chunk, or the item falls to 🟡. We report the unsupported-claim rate. |
| "Privacy?" | Nothing is stored; personal fields stay in the browser; logs hold no personal or health data. |
| "What failed?" | Give the real failures from Day 7. |

---

## 10. Pre-flight checklist (demo day)

- [ ] Live URL works on the venue Wi-Fi and on a hotspot
- [ ] Demo case run end to end 3 times that morning; slider and PDF download checked
- [ ] API quota checked; keys present in Vercel
- [ ] Replay video available offline; backup screenshots in the deck
- [ ] Each member has rehearsed their failure mode and what to say

---

## 11. Submission

**Deck:** at most 10 slides, uploaded to the LMS as .pptx or .pdf.

**Code zip,** submitted at least 2 hours before class, containing:
- `api/`: functions
- `rules/`: engine, what-if, tests
- `pack/`: PDF builder and form maps
- `rag/`: chunk, embed, seed
- `eval/`: labels, splits, v0–v3 scripts, results
- `mcp/`: FastMCP server
- `index.html`, `schema.sql`, `.env.example`, `README.md`

**README covers:**
- where to put `GEMINI_API_KEY`, `SUPABASE_URL` and `SUPABASE_SECRET_KEY`;
- seeding the database;
- running locally;
- re-running the evaluation;
- starting the MCP server.

**Before zipping:** scan the code and the git history for secrets.

---

## 12. Scoring checklist

- **Product (10):** works live; covers the claim before submission (pack and estimate) and after it (audit); AI does the core work.
- **AI (8):** RAG on our own corpus; a multi-step workflow; 6 tools with an MCP bonus; v0→v3 improvement measured against a general-purpose AI baseline.
- **Architecture and cost (5):** the diagram matches the code; the model choice is backed by a benchmark; costs measured per session and at 10,000 users; trade-offs stated.
- **Presentation (7):** the slider moment; the live demo takes half the time; failures stated honestly; Q&A rehearsed.

---

### Sources

- The GenAI Startup Sprint brief (course PDF)
- IRDAI:
  - the proportionate deduction rule (2020);
  - the non-payable item lists I–IV;
  - the health insurance master circular (29 May 2024; summary from [Arthgyaan](https://arthgyaan.com/blog/understanding-latest-irda-master-circular-on-health-insurance-2024.html), to be checked against the circular's text);
  - figures from the FY24 and FY25 annual reports.
- The cashless vs reimbursement split for FY25: [IndiaMedToday, citing IRDAI's annual report](https://indiamedtoday.com/record-health-insurance-claims-settled-in-fy25-average-payout-per-claim-declines/)
- Council for Insurance Ombudsmen: the FY25 annual report, and the *Health_individual April 2021* award compilation (cioins.co.in)
- The LocalCircles survey on health claims (30,366 respondents)
- Product pages for fairClaims (PolicyGaido), ClaimSetu (Policybazaar for Business), ClearTax GST and Insurance Samadhan
- Gemini API: the pricing page, and the deprecation of sampling parameters on 22 Jul 2026 ([AI Weekly](https://aiweekly.co/alerts/google-deprecates-temperature-top-p-and-top-k-in-gemini-36-flash-and-all-future))
