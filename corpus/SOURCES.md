# RAG corpus: source documents for Supabase

The links below were checked on 7 Oct 2026. Some government and insurer sites block scripts, so download the PDFs in a browser and save them to `corpus/raw/` under the file name given for each. Every chunk must be stored with: `doc_id, title, issuer, ref_no, date, status, section, page, url, policy_id`.

**Status rule.** A chunk with `status = in_force` (or `policy_wording`) is the only kind that can support a 🔴 verdict. A `repealed` chunk is shown as background, with the label "Repealed on 29 May 2024; the rule now lives in your policy wording."

## A. Regulatory (doc_type = regulation)

| file | Document | Ref / date | Status | Page with the PDF links | Extract |
|---|---|---|---|---|---|
| `irdai_master_health_2024.pdf` | Master Circular on Health Insurance Business | IRDAI/HLT/CIR/PRO/84/5/2024, 29.05.2024 | in_force | https://irdai.gov.in/document-detail?documentId=4942918 | Paras 15–17: cashless within 1 h, discharge within 3 h, para 17(c) "...Policyholder shall not be required to submit the documents", para 15(a) reimbursement only in exceptional circumstances. Annexure-6 lists the repealed circulars. |
| `irdai_pphi_master_2024.pdf` | Master Circular on Protection of Policyholders' Interests | IRDAI/PP&GR/CIR/MISC/117/9/2024, 05.09.2024 | in_force | https://irdai.gov.in/document-detail?documentId=5625747 | Health para 3(iii)6: non-cashless claims settled "within fifteen days from submission of claim"; interest at bank rate + 2% from the date the intimation was received until payment. Also the disclosure rule for "sub-limits, Proportionate Deductions". |
| `irdai_proportionate_2020.pdf` | Modified Guidelines on Product filing – Norms on Proportionate Deductions | IRDAI/HLT/REG/CIR/151/06/2020, 11.06.2020 | repealed (2024) | https://irdai.gov.in/document-detail?documentId=394680 | Paras 4, 6, 7, 8: no proportionate deduction on pharmacy, consumables, implants, devices, diagnostics or ICU, and none where the hospital does not bill differently by room category. |
| `irdai_standardisation_2020.pdf` | Master Circular on Standardization of Health Insurance Products | IRDAI/HLT/REG/CIR/193/07/2020, 22.07.2020 | repealed (2024); its Annexure I is still referenced by policy wordings | https://irdai.gov.in/document-detail?documentId=395035 | **Annexure I (pp. 26–31):** List I Optional Items; List II subsumed into Room Charges; List III into Procedure Charges; List IV into costs of treatment. Store **one chunk per item**, with the list number. Count the items yourself; an automated count gave 68 / 37 / 23 / 18. |
| `irdai_tpa_master_2020.pdf` | TPA Master Circular | IRDAI/TPA/REG/CIR/130/06/2020, 03.06.2020 | verify current status | https://irdai.gov.in/document-detail?documentId=394530 | **Annexure 30:** standard claim form, Part A (insured) and Part B (hospital). Use its field list to build the Part A form. |

Some IRDAI PDFs are scanned images. Run them through `scripts/ocr_pdf.py` (Gemini, logged as stage `ingest_ocr`), then **a person spot-checks** the paragraphs listed above.

## B. Policy wordings (doc_type = policy_wording, status = policy_wording)

| policy_id | Product, UIN | URL |
|---|---|---|
| `star_fho` | Star Health Family Health Optima, SHAHLIP26046V092526 | https://d28c6jni2fmamz.cloudfront.net/Policy_Family_Health_Optima_Insurance_Plan_V_21_bbe089bd74.pdf (product page: https://www.starhealth.in/health-insurance/family-health-optima/) |
| `niva_reassure2` | Niva Bupa ReAssure 2.0, NBHHLIP27054V032627 | https://transactions.nivabupa.com/pages/doc/policy_wording/ReAssure-2.0-Policy-Wording.pdf |
| `hdfc_optima_secure` | HDFC ERGO my:Optima Secure, HDFHLIP26058V082526 | https://customer-portal-assets.hdfcergo.com/documents/PolicyWordings_myOptimaSecure-76673175551.pdf |
| `care_supreme` | Care Supreme (the UIN differs between the product page and the PDF; record the one printed in the PDF you ingest) | https://cms.careinsurance.com/cms/public/uploads/download_center/care-supreme---policy-terms-and-conditions.pdf |
| `icici_elevate` | ICICI Lombard Elevate, ICIHLIP27057V062627 | https://www.icicilombard.com/docs/default-source/default-document-library/elevate.pdf |

Split each wording into chunks at its numbered clauses. Write the room-rent, proportionate-deduction, definition and claim-procedure clause numbers into `policy_profiles.json`, then set `verified_by_human` to true.

## C. Claim checklists (doc_type = checklist)

- **Star Health:** https://www.starhealth.in/claims/ – reimbursement documents; "within 15 days from the date of discharge".
- **Niva Bupa:** https://transactions.nivabupa.com/claims/pages/health-claim.aspx – "within 30 days from the date of discharge". ReAssure wording 6.2.4b lists the documents.
- **HDFC ERGO:** wording clause 1.6 – within 30 days of discharge; post-hospitalisation within 15 days of completing treatment. No live claims web page was found.

## D. Evaluation data (not loaded into RAG)

- **CIO award compilations** (all opened successfully):
  - https://www.cioins.co.in/GIC/mediclaim/GENERAL_INSURANCE_MEDICLAIM_AWARDS1-10-2014TO31.3.2015.pdf
  - https://www.cioins.co.in/GIC/mediclaim/GENERAL_INSURANCE_MEDICLAIM_APRIL_2015TOSEPT-2015.pdf
  - https://www.cioins.co.in/GIC/mediclaim/Mediclaim-Book14.pdf
  - https://www.cioins.co.in/GIC/groupmediclaim/Group%20Mediclaim-%20Gen27.pdf (group policies, lower priority)
- **The April 2021 compilation** (`.../AwardsMonthwise/Apr2021/Health_individual%20April%202021.pdf`) now returns 404. Seed cases taken from a cached copy are in `eval_seed/award_cases_seed.json`, marked `verified=false`.
- **Older awards come under older rules.** Each case is run against **the terms stated in that award** (its own profile), not today's wordings.
