# ClaimCheck cost report

Generated 2026-10-07 from 16 logged live sessions (pipeline v3). Prices: gemini-3.5-flash-lite $0.3/$2.5 per 1M in/out, gemini-3.6-flash $0.75/$3.75 per 1M in/out, gemini-embedding-2 $0.2/$0.0 per 1M in/out; USD/INR 96.1446.

## One session (upload documents -> checks -> estimate -> explanations)

| Metric | Median | P90 |
|---|---|---|
| Tokens per session | 15,263 | 16,774 |
| Rs per session | 1.10 | 1.21 |
| LLM/embedding calls per session | 9 | 16 |

| Stage | Median tokens | Median input | Median output+thinking | Median calls | Median Rs |
|---|---|---|---|---|---|
| embed_query | 137 | 137 | 0 | 7 | 0.003 |
| extract | 5,374 | 4,020 | 1,354 | 5 | 0.441 |
| generate | 1,808 | 1,200 | 578 | 1 | 0.173 |
| reason | 7,354 | 6,160 | 1,126 | 3 | 0.465 |

What-if slider and pack assembly make no LLM call (Rs 0). The cover letter / grievance letter adds one small generate call when used.

## 10,000 users per month

| Sessions per user per month | Sessions | Median Rs | P90 Rs | + fixed infra |
|---|---|---|---|---|
| 0.2 | 2,000 | 2,207 | 2,412 | 2,207 |
| 1 | 10,000 | 11,036 | 12,060 | 11,036 |
| 3 | 30,000 | 33,107 | 36,181 | 33,107 |

Prices on 3.6 Flash rise on 1 Jan 2027 ($1.50/$7.50); Flash-Lite pricing is unchanged.

## What we would change at scale

1. Flash-Lite has no context caching: keep prompts small by retrieving only the top clauses (already done in v3).
2. Cache the policy context only if a stage moves to Flash (cached input is 90% cheaper).
3. Batch API (50% off) for evaluation reruns and re-embedding the corpus.
4. Route only low-confidence (Review) items to the stronger model.
5. Paid Gemini tier for rate-limit headroom; Supabase Pro and Vercel Pro for capacity; a human-review queue for Review items.
## Run notes (8 Oct 2026, IST)

- Based on 16 complete S1 sessions, run with `scripts/smoke_live.py` against the live API. Every run that reached the estimate reproduced Rs 1,35,125 payable and Rs 58,875 at risk.
- The plan was 20 sessions. The remainder stopped when the Flash-Lite free-tier daily quota (500 requests) was used up.
- "Generated" shows the server's UTC date.
