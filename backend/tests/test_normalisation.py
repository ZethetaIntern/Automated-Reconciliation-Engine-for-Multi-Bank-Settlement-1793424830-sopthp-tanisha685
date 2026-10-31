"""
Unit tests for Normalisation, Decimal Banker's Rounding, and PAN Masking.
"""

from decimal import Decimal
from datetime import datetime
from backend.app.normalisation.security import mask_pan
from backend.app.normalisation.currency import validate_and_format_amount, round_bankers, convert_fx
from backend.app.normalisation.timezone import normalise_to_utc


def test_bankers_rounding_half_even():
    # 2.5 rounds to 2, 3.5 rounds to 4 in bankers rounding
    assert round_bankers(Decimal("2.50000"), 0) == Decimal("2")
    assert round_bankers(Decimal("3.50000"), 0) == Decimal("4")
    # Decimal precision
    assert validate_and_format_amount("1,234.56789", 4) == Decimal("1234.5679")


def test_pan_masking_pci_dss():
    text = "Payment received for card 4532-7592-8832-1234 on POS"
    masked, was_masked = mask_pan(text)
    assert was_masked is True
    assert "4532-7592-8832-1234" not in masked
    assert "1234" in masked


def test_timezone_normalization_to_utc():
    ist_time = datetime(2026, 3, 15, 23, 30, 0)
    utc_time, _ = normalise_to_utc(ist_time, "Asia/Kolkata")
    # 23:30 IST is 18:00 UTC
    assert utc_time.hour == 18
    assert utc_time.minute == 0
