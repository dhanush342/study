"""
Bharat Tech Atlas — Shared utilities for data serialization and formatting.
Single source of truth for row_to_dict and format_funding.
"""
import json


def row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a dict, parsing JSON fields."""
    d = dict(row)
    for field in ["sectors", "data_sources", "investors", "funding_rounds"]:
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
    if "funding_inr" in d and d["funding_inr"]:
        d["funding_crores"] = round(d["funding_inr"] / 10000000, 1)
    else:
        d["funding_crores"] = 0
    return d


def format_funding(amount_inr: float) -> str:
    """Format INR funding amount into human-readable string."""
    if not amount_inr or amount_inr == 0:
        return "Bootstrapped"
    crores = amount_inr / 10000000
    if crores >= 10000:
        return f"₹{crores / 100000:.2f} Lakh Cr"
    if crores >= 100:
        return f"₹{crores:,.0f} Cr"
    if crores >= 1:
        return f"₹{crores:.1f} Cr"
    lakhs = amount_inr / 100000
    return f"₹{lakhs:.0f} L"


def sanitize_like(value: str) -> str:
    """Escape SQL LIKE wildcards in user input."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
