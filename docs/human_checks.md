# Human checks (TODO(HUMAN))

ClaimCheck relies on the items below. A team member must verify each one against the source PDF, then tick it here. In `corpus/policy_profiles.json`, set `verified_by_human` to `true` only once every item for that policy is ticked.

## Policy profiles (`corpus/policy_profiles.json`)

### Star Health Family Health Optima (`star_fho`)

- [ ] **Room-rent bands.** The wording gives Rs 2,000/day for Rs 1–2 lakh sum insured, Rs 5,000/day for Rs 3–4 lakh, and a single standard A/C room from Rs 5 lakh up. Claude checked this against ingested chunk `star_fho-0022`.
- [ ] **Associated medical expenses.** These are nursing, OT and the medical practitioner's professional fees. Pharmacy, consumables, implants, devices, diagnostics and ICU are excluded. Claude checked this against chunk `star_fho-0017`.
- [ ] **Submission deadline.** Claims are due 15 days from discharge (starhealth.in/claims). Compare with the wording at chunk `star_fho-0079`.

### Niva Bupa ReAssure 2.0 (`niva_reassure2`)

- [ ] **Pro-rata formula and associated heads.** These were quoted from the wording. Confirm the clause number.
- [ ] **ICU treatment and submission deadline.** ICU is paid up to the base sum insured; claims are due 30 days from discharge.

### HDFC ERGO my:Optima Secure (`hdfc_optima_secure`)

- [ ] **Room rent.** Room rent is "at actuals unless specified in the Policy Schedule".
- [ ] **Associated expenses.** The wording defines them as consultation fees, OT charges, surgical appliances, nursing, anaesthesia, blood and oxygen. Surgeon fees are not named. Decide how to map them.
- [ ] **Deadline.** Claims are due 30 days from discharge (clause 1.6).

### Care Supreme (`care_supreme`)

- [ ] **UIN.** The product page and the PDF show different UINs. Record the UIN printed on the ingested PDF.
- [ ] **Submission deadline.** Find it in the wording (currently TO VERIFY).

### ICICI Lombard Elevate (`icici_elevate`)

- [ ] **Associated heads and deadline.** Both are currently TO VERIFY.

## Regulatory corpus

- [ ] **Annexure I item counts.** Check the counts per list against pages 26–31 of IRDAI/HLT/REG/CIR/193/07/2020. The parser found List I 1–68, List II 1–37, List III 1–23 and List IV 1–18; see `/api/admin/search?doc_types=non_payable_item`.
- [ ] **Master circular paragraphs.** Spot-check paras 15–17 of IRDAI/HLT/CIR/PRO/84/5/2024: reimbursement only in exceptional circumstances, and documents to be collected from hospitals.
- [ ] **15-day settlement rule.** Spot-check health para 3(iii)6 of IRDAI/PP&GR/CIR/MISC/117/9/2024: claims settled within 15 days of submission, with interest at bank rate + 2%.
- [ ] **Interest basis.** Confirm how indicative interest should be counted, from intimation or from submission. ClaimCheck currently counts days from the intimation date and labels the result "indicative".

## Claim form Part A (`claimcheck/pack.py` `PART_A`)

- [ ] **Field list.** Check section titles and fields against Annexure 30 of IRDAI/TPA/REG/CIR/130/06/2020. That document is ingested as `doc_type='claim_form'`.

## Evaluation data

- [ ] **Ombudsman cases.** Verify the seed award cases in `eval_seed/award_cases_seed.json` against a source copy. The April 2021 compilation now returns 404. Add 15 or more verified cases from the live CIO compilations listed in `corpus/SOURCES.md`.
