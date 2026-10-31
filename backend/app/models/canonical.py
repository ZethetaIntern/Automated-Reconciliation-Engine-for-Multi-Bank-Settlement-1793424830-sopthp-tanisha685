"""
Canonical Data Model for Multi-Bank Settlement Reconciliation Engine.
Strictly adheres to Section A2.4 of the specification.
Uses fixed-point Decimal arithmetic (ROUND_HALF_EVEN) to prevent floating-point drift.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


def _now_utc():
    return datetime.now(timezone.utc)


class DirectionEnum(str, Enum):
    CR = "CR"  # Credit
    DR = "DR"  # Debit


class SourceFormatEnum(str, Enum):
    CSV = "CSV"
    MT940 = "MT940"
    CAMT053 = "CAMT.053"
    INTERNAL_LEDGER = "INTERNAL_LEDGER"
    API_FEED = "API_FEED"


class CanonicalTransaction(BaseModel):
    """
    The 10 canonical fields defined in Section A2.4 of Zetheta specification.
    Serves as the single source of truth across all banking formats.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    txn_id: str = Field(..., max_length=64, description="Unique transaction identifier")
    txn_date: datetime = Field(..., description="Transaction booking date/time in UTC")
    amount: Decimal = Field(..., description="Transaction amount in fixed-point decimal")
    currency: str = Field(default="INR", max_length=3, description="ISO 4217 3-letter currency code")
    direction: DirectionEnum = Field(..., description="Debit or Credit indicator (DR/CR)")
    counterparty_name: Optional[str] = Field(default="", max_length=140, description="Name of counterparty")
    counterparty_account: Optional[str] = Field(default="", max_length=34, description="Counterparty Account or IBAN")
    bank_ref: Optional[str] = Field(default="", max_length=64, description="Bank internal reference number")
    narration: Optional[str] = Field(default="", max_length=500, description="Free-text transaction narration/remarks")
    settlement_date: Optional[date] = Field(default=None, description="Settlement/value date")

    # System & Audit metadata
    source_format: SourceFormatEnum = Field(default=SourceFormatEnum.CSV)
    source_file: str = Field(default="")
    bank_code: str = Field(default="INTERNAL")
    raw_payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ingested_at: datetime = Field(default_factory=_now_utc)
    is_masked: bool = Field(default=False, description="Whether sensitive data (PAN) has been masked")

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not v:
            return "INR"
        cleaned = str(v).strip().upper()
        if len(cleaned) != 3:
            return "INR"
        return cleaned

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        if isinstance(v, Decimal):
            return v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        if isinstance(v, (int, float)):
            return Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        if isinstance(v, str):
            # Clean commas or whitespace
            cleaned = v.replace(",", "").replace(" ", "").strip()
            if not cleaned:
                return Decimal("0.0000")
            return Decimal(cleaned).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        return Decimal("0.0000")

    @field_validator("direction", mode="before")
    @classmethod
    def validate_direction(cls, v: Any) -> DirectionEnum:
        if isinstance(v, DirectionEnum):
            return v
        s = str(v).strip().upper()
        if s in ("CR", "C", "CREDIT", "RC"):
            return DirectionEnum.CR
        if s in ("DR", "D", "DEBIT", "RD"):
            return DirectionEnum.DR
        return DirectionEnum.CR

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary with stringified decimals."""
        return {
            "txn_id": self.txn_id,
            "txn_date": self.txn_date.isoformat(),
            "amount": str(self.amount),
            "currency": self.currency,
            "direction": self.direction.value,
            "counterparty_name": self.counterparty_name or "",
            "counterparty_account": self.counterparty_account or "",
            "bank_ref": self.bank_ref or "",
            "narration": self.narration or "",
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "source_format": self.source_format.value,
            "source_file": self.source_file,
            "bank_code": self.bank_code,
            "is_masked": self.is_masked,
        }
