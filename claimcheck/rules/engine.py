"""Deterministic rules engine. Pure functions: no I/O, no LLM. Every rupee the user sees comes from here."""
import json, os
from datetime import date
from claimcheck import config

_PROFILES = None


def profiles() -> dict:
    global _PROFILES
    if _PROFILES is None:
        with open(os.path.join(config.ROOT, "corpus", "policy_profiles.json")) as f:
            _PROFILES = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    return _PROFILES


def profile(policy_id: str) -> dict:
    p = profiles().get(policy_id)
    if not p:
        raise ValueError(f"unknown policy_id {policy_id}")
    return p


def rnd(x: float) -> int:
    """Round half up to whole rupees (amounts are non-negative)."""
    return int(x + 0.5)


def eligible_room_rent(prof: dict, sum_insured: int, user_value: int | None):
    """Returns (eligible_per_day or None for 'no limit', source_text)."""
    rr = prof.get("room_rent", {})
    t = rr.get("type")
    if t == "per_day_cap_by_sum_insured":
        for b in rr["bands"]:
            if sum_insured >= b["si_from"] and (b["si_to"] is None or sum_insured <= b["si_to"]):
                if b.get("cap_per_day"):
                    return b["cap_per_day"], f"policy cap Rs {b['cap_per_day']:,}/day for this sum insured"
                return user_value, f"eligible category: {b.get('category')} (enter that room's tariff)"
        return user_value, "sum insured outside the profile bands - enter eligible rent"
    if t in ("no_limit",):
        return None, "no room-rent limit"
    if t == "at_actuals_unless_schedule_specifies":
        return (user_value, "limit from your policy schedule") if user_value else (None, "room rent at actuals")
    # eligible_category_from_schedule / limit_or_category_from_schedule
    return user_value, ("hospital tariff for your eligible room category" if user_value else
                        "enter the hospital's tariff for your eligible room category")


def _room_line(items):
    return next((i for i in items if i["category"] == "room"), None)


def _rule_active(rt):
    return rt if (rt in config.ACTIVE_RULE_TYPES or rt == "UNKNOWN") else "UNKNOWN"


def estimate_settlement(policy_id: str, sum_insured: int, items: list[dict], assignments: list[dict],
                        eligible_room_rent_per_day: int | None = None, room_rent_per_day: int | None = None,
                        evidence: dict | None = None) -> dict:
    """items: confirmed line items; assignments: RuleAssignment dicts from the reasoning agent.
    room_rent_per_day: what-if override of the room line's daily rate (other charges held constant).
    evidence: {line_id: bool} result of the verbatim-quote check (missing => False)."""
    prof = profile(policy_id)
    evidence = evidence or {}
    amap = {a["line_id"]: a for a in assignments}
    items = [dict(i) for i in items]
    room = _room_line(items)
    days = (room or {}).get("room_days") or 0
    if room and room_rent_per_day is not None and days:
        room["amount"] = room_rent_per_day * days
    actual = rnd(room["amount"] / days) if room and days else None
    eligible, elig_src = eligible_room_rent(prof, sum_insured, eligible_room_rent_per_day)
    prop_on = prof.get("proportionate_deduction") in (True, "only_if_schedule_sets_a_limit")
    ratio = eligible / actual if (prop_on and eligible and actual and actual > eligible) else 1.0
    assoc = set(prof.get("associated_expense_heads") or []) if isinstance(prof.get("associated_expense_heads"), list) else set()
    never = set(prof.get("never_proportionate") or [])

    out, tot_amt, tot_pay = [], 0, 0
    for it in items:
        a = amap.get(it["line_id"], {})
        model_rt = _rule_active(a.get("rule_type", "UNKNOWN"))
        amt, cat = it["amount"], it["category"]
        notes = []
        if model_rt == "NON_PAYABLE_LIST_I":
            rt, pay, formula = "NON_PAYABLE_LIST_I", 0, f"Listed non-payable item: payable = 0 (of Rs {amt:,})"
        elif model_rt == "SUBSUMED_LIST_II_IV":
            rt, pay, formula = "SUBSUMED_LIST_II_IV", 0, f"Payable only within its parent head; billed separately: Rs {amt:,} at risk"
            notes.append("subsumed item billed separately")
        elif ratio < 1 and cat in assoc and cat not in never:
            if it.get("billed_by_room_category") is False:
                rt, pay, formula = "NO_DEDUCTION", amt, "Hospital does not bill this head by room category: no proportionate deduction"
                notes.append("differential billing not followed for this head")
            else:
                rt = "ROOM_RENT_CAP" if cat == "room" else "PROPORTIONATE_DEDUCTION"
                pay = rnd(amt * ratio)
                formula = f"Rs {amt:,} x ({eligible:,} / {actual:,}) = Rs {pay:,}"
        else:
            rt, pay = "NO_DEDUCTION", amt
            formula = (f"{cat.replace('_', ' ')} is excluded from proportionate deduction: payable in full"
                       if (ratio < 1 and cat in never) else "No deduction rule applies: payable in full")
        at_risk = amt - pay
        if model_rt not in (rt, "UNKNOWN") and not (model_rt == "NO_DEDUCTION" and rt == "NO_DEDUCTION"):
            notes.append(f"model suggested {model_rt}; engine applied {rt}")
        high = bool(it.get("confirmed", True)) and bool(evidence.get(it["line_id"])) and model_rt == rt and rt != "UNKNOWN"
        if at_risk > 0:
            verdict = "AT_RISK" if high else "REVIEW"
        else:
            verdict = "PAYABLE" if it.get("confirmed", True) and not notes else "REVIEW"
        out.append(dict(line_id=it["line_id"], description=it["description"], category=cat, amount=amt, payable=pay,
                        at_risk=at_risk, rule_type=rt, model_rule_type=model_rt, formula=formula,
                        confidence="high" if high else "low", verdict=verdict, notes=notes,
                        policy_chunk_id=a.get("policy_chunk_id"), policy_quote=a.get("policy_quote"),
                        regulatory_chunk_id=a.get("regulatory_chunk_id"), regulatory_quote=a.get("regulatory_quote")))
        tot_amt += amt
        tot_pay += pay

    adjustments = []
    pay_after = tot_pay
    ded = prof.get("deductible") or 0
    if isinstance(ded, int) and ded:
        adjustments.append(dict(rule_type="DEDUCTIBLE", amount=min(ded, pay_after))); pay_after -= min(ded, pay_after)
    cp = prof.get("copay_pct") or 0
    if isinstance(cp, (int, float)) and cp:
        c = rnd(pay_after * cp); adjustments.append(dict(rule_type="COPAY", amount=c)); pay_after -= c
    if pay_after > sum_insured:
        adjustments.append(dict(rule_type="SUM_INSURED_CAP", amount=pay_after - sum_insured)); pay_after = sum_insured
    return dict(policy_id=policy_id, sum_insured=sum_insured, total_billed=tot_amt, payable=pay_after,
                at_risk=tot_amt - pay_after, ratio=round(ratio, 6), eligible_room_rent_per_day=eligible,
                eligible_source=elig_src, actual_room_rent_per_day=actual, room_days=days or None,
                items=out, adjustments=adjustments)


ROOM_RELATED = ("PROPORTIONATE_DEDUCTION", "ROOM_RENT_CAP")


def simulate_whatif(policy_id, sum_insured, items, assignments, eligible_room_rent_per_day, room_rent_values,
                    evidence=None) -> list[dict]:
    res = []
    for v in room_rent_values:
        e = estimate_settlement(policy_id, sum_insured, items, assignments, eligible_room_rent_per_day, v, evidence)
        res.append(dict(room_rent_per_day=v, payable=e["payable"], at_risk_total=e["at_risk"],
                        at_risk_room_related=sum(i["at_risk"] for i in e["items"] if i["rule_type"] in ROOM_RELATED)))
    return res


def audit_settlement(estimate: dict, per_head_paid: dict) -> dict:
    tol = config.TOLERANCE_INR
    rows, total_var = [], 0
    for i in estimate["items"]:
        paid = per_head_paid.get(i["line_id"])
        if paid is None:
            rows.append(dict(line_id=i["line_id"], description=i["description"], estimated=i["payable"], paid=None,
                             variance=None, verdict="REVIEW", note="no paid amount entered")); continue
        var = i["payable"] - paid
        total_var += var
        if abs(var) <= tol:
            verdict = "SUPPORTED"
        elif var > tol and i["confidence"] == "high":
            verdict = "POTENTIAL_INCONSISTENCY"
        else:
            verdict = "REVIEW"
        rows.append(dict(line_id=i["line_id"], description=i["description"], estimated=i["payable"], paid=paid,
                         variance=var, verdict=verdict, rule_type=i["rule_type"], formula=i["formula"],
                         policy_quote=i.get("policy_quote"), policy_chunk_id=i.get("policy_chunk_id")))
    return dict(rows=rows, total_estimated=estimate["payable"], total_paid=sum(v for v in per_head_paid.values()),
                variance=total_var)


def settlement_timeline(intimation_date, submission_date, settlement_date, paid: int, bank_rate: float | None):
    if not (submission_date and settlement_date):
        return dict(checked=False, note="enter submission and settlement dates")
    sub, setl = date.fromisoformat(submission_date), date.fromisoformat(settlement_date)
    days = (setl - sub).days
    out = dict(checked=True, settlement_days_after_submission=days, limit_days=config.SETTLEMENT_DAYS_LIMIT,
               beyond_limit=days > config.SETTLEMENT_DAYS_LIMIT)
    if out["beyond_limit"] and bank_rate is not None and intimation_date:
        idays = (setl - date.fromisoformat(intimation_date)).days
        out["indicative_interest"] = dict(rate=round(bank_rate + config.INTEREST_SPREAD, 6), days=idays,
                                          amount=rnd(paid * (bank_rate + config.INTEREST_SPREAD) * idays / 365))
    elif out["beyond_limit"]:
        out["note"] = "enter the RBI bank rate and intimation date to compute indicative interest"
    return out
