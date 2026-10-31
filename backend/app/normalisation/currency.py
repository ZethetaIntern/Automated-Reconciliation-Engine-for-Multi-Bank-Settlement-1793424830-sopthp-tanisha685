"""
Currency normalisation, Decimal math, and FX conversion with tolerance bands.
Uses banker's rounding (ROUND_HALF_EVEN) per RBI & NPCI settlement standards.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Dict, Optional, Tuple

VALID_ISO_CURRENCIES = {
    "INR", "USD", "EUR", "GBP", "SGD", "AED", "JPY", "CAD", "AUD", "CHF", "CNY", "HKD"
}

# Default RBI reference rates against INR (as of simulation baseline)
DEFAULT_FX_RATES: Dict[str, Decimal] = {
    "INR": Decimal("1.0000"),
    "USD": Decimal("83.2500"),
    "EUR": Decimal("90.4500"),
    "GBP": Decimal("105.8000"),
    "SGD": Decimal("61.5000"),
    "AED": Decimal("22.6500"),
    "JPY": Decimal("0.5500"),
}


def round_bankers(val: Decimal, places: int = 4) -> Decimal:
    """Quantize to specified places using ROUND_HALF_EVEN (Banker's Rounding)."""
    q_str = "0." + ("0" * places) if places > 0 else "1"
    return val.quantize(Decimal(q_str), rounding=ROUND_HALF_EVEN)


def validate_and_format_amount(raw_amount: any, places: int = 4) -> Decimal:
    """Safely converts input into exact fixed-point Decimal."""
    if isinstance(raw_amount, Decimal):
        return round_bankers(raw_amount, places)
    if isinstance(raw_amount, (int, float)):
        return round_bankers(Decimal(str(raw_amount)), places)
    if isinstance(raw_amount, str):
        cleaned = raw_amount.replace(",", "").replace(" ", "").strip()
        if not cleaned:
            return Decimal("0.0000")
        return round_bankers(Decimal(cleaned), places)
    return Decimal("0.0000")


def convert_fx(
    amount: Decimal,
    from_currency: str,
    to_currency: str = "INR",
    applied_rate: Optional[Decimal] = None
) -> Tuple[Decimal, Decimal, float]:
    """
    Converts amount from one currency to another.
    Returns (converted_amount, applied_rate, variance_percentage).
    """
    from_curr = from_curr.upper() if (from_curr := from_currency) else "INR"
    to_curr = to_curr.upper() if (to_curr := to_currency) else "INR"

    if from_curr == to_curr:
        return amount, Decimal("1.0000"), 0.0

    ref_rate = DEFAULT_FX_RATES.get(from_curr, Decimal("1.0000"))
    rate_to_use = applied_rate if applied_rate is not None else ref_rate

    # Variance against reference rate
    if ref_rate > 0:
        variance = float(abs(rate_to_use - ref_rate) / ref_rate)
    else:
        variance = 0.0

    converted = round_bankers(amount * rate_to_use, 4)
    return converted, rate_to_use, variance
