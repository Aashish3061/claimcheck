"""Pydantic models for LLM I/O and API I/O."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

DocType = Literal["final_bill", "itemised_bill", "discharge_summary", "pharmacy_bill", "prescription",
                  "investigation_report", "tariff_card", "settlement_letter", "id_proof", "other"]
Category = Literal["room", "icu", "nursing", "medical_practitioner_fees", "ot_charges", "pharmacy", "consumables",
                   "implants", "medical_devices", "diagnostics", "non_payable_candidate", "other"]
RuleType = Literal["PROPORTIONATE_DEDUCTION", "ROOM_RENT_CAP", "NON_PAYABLE_LIST_I", "SUBSUMED_LIST_II_IV",
                   "COPAY", "DEDUCTIBLE", "NO_DEDUCTION", "UNKNOWN"]


# ---------- extraction (LLM output) ----------
class LineItem(BaseModel):
    line_id: str = Field(description="L1, L2, ... in bill order")
    description: str
    category: Category
    quantity: Optional[float] = None
    unit_rate: Optional[int] = None
    amount: int = Field(description="integer rupees")
    room_days: Optional[int] = Field(default=None, description="days, only for room/ICU lines")


class TariffRow(BaseModel):
    room_category: str
    rate_per_day: int


class ExtractedDoc(BaseModel):
    doc_type: DocType
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    admission_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    discharge_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    line_items: list[LineItem] = []
    stated_total: Optional[int] = None
    tariff: list[TariffRow] = []
    notes: Optional[str] = Field(default=None, description="e.g. 'charges vary by room category'")


# ---------- reasoning (LLM output) ----------
class RuleAssignment(BaseModel):
    line_id: str
    rule_type: RuleType
    policy_chunk_id: Optional[str] = None
    policy_quote: Optional[str] = Field(default=None, description="verbatim text copied from the policy chunk")
    regulatory_chunk_id: Optional[str] = None
    regulatory_quote: Optional[str] = None
    non_payable_list_no: Optional[int] = None


class Assignments(BaseModel):
    assignments: list[RuleAssignment]


# ---------- v0 baseline (LLM output, evaluation only) ----------
class V0Item(BaseModel):
    description: str
    amount: int
    payable: int
    reason: str


class V0Estimate(BaseModel):
    total_billed: int
    payable: int
    at_risk: int
    items: list[V0Item]


# ---------- generation (LLM output) ----------
class Explanation(BaseModel):
    line_id: str
    text: str


class Explanations(BaseModel):
    explanations: list[Explanation]


class Letter(BaseModel):
    subject: str
    body: str


# ---------- API inputs ----------
class ConfirmedItem(BaseModel):
    line_id: str
    description: str
    category: Category
    amount: int
    room_days: Optional[int] = None
    confirmed: bool = True
    billed_by_room_category: Optional[bool] = None


class DocSummary(BaseModel):
    doc_type: DocType
    patient_name: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    stated_total: Optional[int] = None
    line_total: Optional[int] = None


class ChecksIn(BaseModel):
    policy_id: str
    docs: list[DocSummary]
    has_diagnostics: bool = False
    today: Optional[str] = None


class EstimateIn(BaseModel):
    policy_id: str
    sum_insured: int
    items: list[ConfirmedItem]
    eligible_room_rent_per_day: Optional[int] = None


class WhatIfIn(EstimateIn):
    assignments: list[RuleAssignment]
    room_rent_values: list[int]


class PackIn(BaseModel):
    policy_id: str
    estimate: dict
    checks: dict
    personal: dict = {}
    docs_present: list[str] = []


class AuditIn(BaseModel):
    policy_id: str
    estimate: dict
    per_head_paid: dict[str, int]
    intimation_date: Optional[str] = None
    submission_date: Optional[str] = None
    settlement_date: Optional[str] = None
    bank_rate: Optional[float] = None
    selected_line_ids: list[str] = []
    write_letter: bool = False
