# ClaimCheck evaluation report

Synthetic cases with known ground truth (fictional hospitals and patients; policy terms from public wordings). Precision/recall are per bill line; CI = Wilson 95%.

| Split | Version | Model | Thinking | Cases | Extraction acc. | At-risk precision (95% CI) | Recall (flag) | Recall incl. Review | Median payable error (Rs) | Citation validity | Unsupported numbers | Rs/case median (P90) | Latency s median (P90) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | v0 | gemini-3.5-flash-lite | low | 9 (0 failed) | n/a | 10/13 = 77% (50%-92%) | 10/17 = 59% | 59% | 186 | n/a | 0 | 1.19 (1.29) | 5.6 (5.9) |
| dev | v1 | gemini-3.5-flash-lite | low | 9 (0 failed) | 249/250 = 100% | 10/12 = 83% (55%-95%) | 10/17 = 59% | 59% | 9500 | n/a | 0 | 1.58 (1.60) | 20.6 (41.7) |
| dev | v2 | gemini-3.5-flash-lite | low | 9 (0 failed) | 249/250 = 100% | 15/15 = 100% (80%-100%) | 15/17 = 88% | 88% | 0 | 39/55 = 71% | 0 | 1.67 (1.81) | 12.7 (66.2) |
| dev | v3 | gemini-3.5-flash-lite | low | 9 (0 failed) | 249/250 = 100% | 17/17 = 100% (82%-100%) | 17/17 = 100% | 100% | 0 | 55/55 = 100% | 0 | 0.79 (0.90) | 20.6 (48.4) |
| test | v0 | gemini-3.5-flash-lite | low | 3 (0 failed) | n/a | 4/4 = 100% (51%-100%) | 4/6 = 67% | 67% | 2972 | n/a | 0 | 1.17 (1.23) | 4.9 (5.0) |
| test | v1 | gemini-3.5-flash-lite | low | 3 (0 failed) | 77/77 = 100% | 6/6 = 100% (61%-100%) | 6/6 = 100% | 100% | 3715 | n/a | 0 | 1.48 (1.77) | 10.8 (42.2) |
| test | v2 | gemini-3.5-flash-lite | low | 3 (0 failed) | 77/77 = 100% | 5/5 = 100% (57%-100%) | 5/6 = 83% | 100% | 0 | 8/15 = 53% | 0 | 1.62 (1.65) | 11.9 (12.2) |
| test | v3 | gemini-3.5-flash-lite | low | 3 (0 failed) | 77/77 = 100% | 6/6 = 100% (61%-100%) | 6/6 = 100% | 100% | 0 | 17/17 = 100% | 0 | 0.70 (0.81) | 14.6 (45.8) |
| val | v0 | gemini-3.5-flash-lite | low | 3 (0 failed) | n/a | 6/6 = 100% (61%-100%) | 6/6 = 100% | 100% | 0 | n/a | 0 | 1.19 (1.27) | 4.9 (35.2) |
| val | v1 | gemini-3.5-flash-lite | low | 3 (0 failed) | 84/84 = 100% | 6/6 = 100% (61%-100%) | 6/6 = 100% | 100% | 500 | n/a | 0 | 1.60 (1.77) | 12.1 (14.7) |
| val | v2 | gemini-3.5-flash-lite | low | 3 (0 failed) | 84/84 = 100% | 6/6 = 100% (61%-100%) | 6/6 = 100% | 100% | 0 | 18/19 = 95% | 0 | 1.74 (1.80) | 12.5 (12.7) |
| val | v3 | gemini-3.5-flash-lite | low | 3 (0 failed) | 84/84 = 100% | 5/5 = 100% (57%-100%) | 5/6 = 83% | 100% | 0 | 18/19 = 95% | 0 | 0.82 (0.96) | 17.2 (51.3) |
| val | v3 | gemini-3.6-flash | low | 3 (1 failed) | 54/54 = 100% | 1/1 = 100% (21%-100%) | 1/1 = 100% | 100% | 0.0 | 12/12 = 100% | 0 | 0.91 (1.15) | 68.9 (72.5) |

## What failed

- dev/v0/gemini-3.5-flash-lite: S1 payable error Rs 55,875, FP 0, FN 5
- dev/v0/gemini-3.5-flash-lite: S3 payable error Rs 186, FP 1, FN 0
- dev/v0/gemini-3.5-flash-lite: V01 payable error Rs 22,400, FP 1, FN 0
- dev/v0/gemini-3.5-flash-lite: V03 payable error Rs 26,700, FP 1, FN 0
- dev/v0/gemini-3.5-flash-lite: V06 payable error Rs 18,929, FP 0, FN 2
- dev/v1/gemini-3.5-flash-lite: S1 payable error Rs 54,475, FP 0, FN 5
- dev/v1/gemini-3.5-flash-lite: S2 payable error Rs 9,500, FP 0, FN 0
- dev/v1/gemini-3.5-flash-lite: S3 payable error Rs 14,500, FP 1, FN 0
- dev/v1/gemini-3.5-flash-lite: V01 payable error Rs 3,000, FP 0, FN 0
- dev/v1/gemini-3.5-flash-lite: V02 payable error Rs 9,500, FP 0, FN 0
- dev/v1/gemini-3.5-flash-lite: V03 payable error Rs 5,000, FP 0, FN 0
- dev/v1/gemini-3.5-flash-lite: V04 payable error Rs 4,000, FP 1, FN 0
- dev/v1/gemini-3.5-flash-lite: V05 payable error Rs 12,500, FP 0, FN 0
- dev/v1/gemini-3.5-flash-lite: V06 payable error Rs 19,429, FP 0, FN 2
- dev/v2/gemini-3.5-flash-lite: S2 payable error Rs 300, FP 0, FN 1
- dev/v2/gemini-3.5-flash-lite: V05 payable error Rs 500, FP 0, FN 1
- test/v0/gemini-3.5-flash-lite: V10 payable error Rs 2,972, FP 0, FN 0
- test/v0/gemini-3.5-flash-lite: V12 payable error Rs 9,300, FP 0, FN 2
- test/v1/gemini-3.5-flash-lite: V10 payable error Rs 3,715, FP 0, FN 0
- test/v1/gemini-3.5-flash-lite: V11 payable error Rs 5,000, FP 0, FN 0
- test/v2/gemini-3.5-flash-lite: V12 payable error Rs 0, FP 0, FN 1
- val/v0/gemini-3.5-flash-lite: V07 payable error Rs 7,400, FP 0, FN 0
- val/v1/gemini-3.5-flash-lite: V08 payable error Rs 9,500, FP 0, FN 0
- val/v1/gemini-3.5-flash-lite: V09 payable error Rs 500, FP 0, FN 0
- val/v3/gemini-3.5-flash-lite: V07 payable error Rs 0, FP 0, FN 1
- val/v3/gemini-3.6-flash: V07 errored: LLMError: ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https

Award cases from Ombudsman compilations are not yet included: none are verified (see docs/human_checks.md).
## Run notes (8 Oct 2026, IST)

- All 15 cases ran on v0 to v3 with gemini-3.5-flash-lite. The test split (V10 to V12) ran once only.
- gemini-3.6-flash benchmark on val: V08 and V09 completed (payable exact, citations 12/12 valid). V07 hit the 3.6 Flash free-tier rate limit (429) on every attempt, so it is a quota failure, not a model failure.
