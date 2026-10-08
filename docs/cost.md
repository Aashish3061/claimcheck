# ClaimCheck cost report

Generated 2026-10-07 from 22 logged live sessions (pipeline v3). Prices: gemini-3.5-flash-lite $0.3/$2.5 per 1M in/out, gemini-3.6-flash $0.75/$3.75 per 1M in/out, gemini-embedding-2 $0.2/$0.0 per 1M in/out; USD/INR 96.1446.

## One session (upload documents -> checks -> estimate -> explanations)

| Metric | Median | P90 |
|---|---|---|
| Tokens per session | 15,926 | 16,774 |
| Rs per session | 1.14 | 1.26 |
| LLM/embedding calls per session | 10 | 19 |

| Stage | Median tokens | Median input | Median output+thinking | Median calls | Median Rs |
|---|---|---|---|---|---|
| embed_query | 170 | 170 | 0 | 9 | 0.003 |
| extract | 5,373 | 4,020 | 1,353 | 5 | 0.441 |
| generate | 1,846 | 1,212 | 635 | 1 | 0.189 |
| reason | 7,562 | 6,193 | 1,159 | 3 | 0.482 |

What-if slider and pack assembly make no LLM call (Rs 0). The cover letter / grievance letter adds one small generate call when used.

## 10,000 users per month

| Sessions per user per month | Sessions | Median Rs | P90 Rs | + fixed infra |
|---|---|---|---|---|
| 0.2 | 2,000 | 2,278 | 2,521 | 2,278 |
| 1 | 10,000 | 11,390 | 12,607 | 11,390 |
| 3 | 30,000 | 34,171 | 37,820 | 34,171 |

Prices on 3.6 Flash rise on 1 Jan 2027 ($1.50/$7.50); Flash-Lite pricing is unchanged.

## What we would change at scale

1. Flash-Lite has no context caching: keep prompts small by retrieving only the top clauses (already done in v3).
2. Cache the policy context only if a stage moves to Flash (cached input is 90% cheaper).
3. Batch API (50% off) for evaluation reruns and re-embedding the corpus.
4. Route only low-confidence (Review) items to the stronger model.
5. Paid Gemini tier for rate-limit headroom; Supabase Pro and Vercel Pro for capacity; a human-review queue for Review items.
## Run notes (8 Oct 2026, IST)

- Based on 22 complete S1 sessions against the live API: 21 runs of `scripts/smoke_live.py` plus the browser run that recorded `public/replay/s1.json`. Every run that reached the estimate reproduced Rs 1,35,125 payable and Rs 58,875 at risk.
- "Generated" shows the server's UTC date.
