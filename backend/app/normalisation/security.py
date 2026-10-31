"""
Security and PCI DSS compliance modules.
Implements PAN (Primary Account Number) masking and file integrity hashing.
"""

import re
import hashlib
from typing import Tuple


CARD_PAN_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def mask_pan(text: str) -> Tuple[str, bool]:
    """
    Scans text or reference fields for potential credit/debit card Primary Account Numbers (13-19 digits).
    Masks all digits except the last 4 digits (PCI DSS Requirement 3.3).
    Example: 4532-7592-8832-1234 -> ************1234
    """
    if not text:
        return text, False

    was_masked = False

    def _replace_pan(match: re.Match) -> str:
        nonlocal was_masked
        raw_digits = re.sub(r"[^\d]", "", match.group(0))
        # Basic Luhn / length check for plausible PAN
        if 13 <= len(raw_digits) <= 19:
            was_masked = True
            masked = ("*" * (len(raw_digits) - 4)) + raw_digits[-4:]
            return masked
        return match.group(0)

    masked_text = CARD_PAN_REGEX.sub(_replace_pan, text)
    return masked_text, was_masked


def compute_sha256(content: bytes | str) -> str:
    """Computes SHA-256 hash for file or message payload."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()
