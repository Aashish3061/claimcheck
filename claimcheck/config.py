"""All tunables live here. Secrets come only from environment variables."""
import os
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS = {
    "extract": "gemini-3.5-flash-lite",
    "reason": "gemini-3.5-flash-lite",
    "generate": "gemini-3.5-flash-lite",
    "ocr": "gemini-3.5-flash-lite",
    "bench": "gemini-3.6-flash",
    "embed": "gemini-embedding-2",
}
EMBED_DIM = 768
# thinking_level per stage (Gemini 3.x: minimal | low | medium | high). Never send temperature/top_p/top_k.
THINKING = {"extract": "minimal", "reason": "low", "generate": "minimal", "ocr": "minimal", "v0": "low"}
PIPELINE_VERSION = os.getenv("PIPELINE_VERSION", "v3")
MAX_TOOL_ROUNDS = 2  # seed retrieval covers most needs; keeps the demo fast

# Prices: USD per 1M tokens, (effective_from, input, output_incl_thinking, cached_input or None)
# Source: https://ai.google.dev/gemini-api/docs/pricing (checked 7 Oct 2026)
PRICES = {
    "gemini-3.5-flash-lite": [("2026-01-01", 0.30, 2.50, None)],
    "gemini-3.6-flash": [("2026-01-01", 0.75, 3.75, 0.075), ("2027-01-01", 1.50, 7.50, 0.15)],
    "gemini-3.5-flash": [("2026-01-01", 1.50, 9.00, None)],
    "gemini-embedding-2": [("2026-01-01", 0.20, 0.0, None)],
}
USD_INR = 96.1446  # 2 Oct 2026

RULE_TYPES = ["PROPORTIONATE_DEDUCTION", "ROOM_RENT_CAP", "NON_PAYABLE_LIST_I", "SUBSUMED_LIST_II_IV",
              "COPAY", "DEDUCTIBLE", "NO_DEDUCTION", "UNKNOWN"]
# Set after the Day-2 data review; inactive types are treated as UNKNOWN (=> Review).
ACTIVE_RULE_TYPES = set(os.getenv("ACTIVE_RULE_TYPES",
    "PROPORTIONATE_DEDUCTION,ROOM_RENT_CAP,NON_PAYABLE_LIST_I,SUBSUMED_LIST_II_IV,NO_DEDUCTION").split(","))
TOLERANCE_INR = int(os.getenv("TOLERANCE_INR", "10"))
DAILY_SESSION_CAP = int(os.getenv("DAILY_SESSION_CAP", "300"))
ADMIN_ENABLED = os.getenv("ADMIN_ENABLED") == "1"  # turn on only while ingesting / evaluating
SETTLEMENT_DAYS_LIMIT = 15  # IRDAI/PP&GR/CIR/MISC/117/9/2024, health para 3(iii)6
INTEREST_SPREAD = 0.02      # bank rate + 2%


def price(model: str, on: date | None = None):
    on = (on or date.today()).isoformat()
    rows = [r for r in PRICES[model] if r[0] <= on]
    return rows[-1] if rows else PRICES[model][0]


def cost_inr(model: str, prompt=0, output=0, thoughts=0, cached=0, tool_prompt=0, on: date | None = None) -> float:
    _, p_in, p_out, p_cache = price(model, on)
    uncached = max(prompt + tool_prompt - cached, 0)
    usd = (uncached * p_in + cached * (p_cache if p_cache is not None else p_in) + (output + thoughts) * p_out) / 1e6
    return round(usd * USD_INR, 6)
