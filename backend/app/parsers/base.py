"""
Base parser interface and parse result container.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from decimal import Decimal
from pydantic import BaseModel

from backend.app.models.canonical import CanonicalTransaction


class BalanceReport(BaseModel):
    opening_balance: Optional[Decimal] = None
    opening_balance_date: Optional[str] = None
    closing_balance: Optional[Decimal] = None
    closing_balance_date: Optional[str] = None
    currency: str = "INR"
    account_number: Optional[str] = None
    statement_number: Optional[str] = None


class ParseResult(BaseModel):
    transactions: List[CanonicalTransaction]
    parse_errors: List[Dict[str, Any]]
    total_records: int
    successful_records: int
    file_sha256: str
    balances: Optional[BalanceReport] = None
    metadata: Dict[str, Any] = {}


class BaseParser(ABC):
    @abstractmethod
    def parse_content(
        self,
        content: str | bytes,
        filename: str,
        bank_code: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        """Parse raw file content into CanonicalTransactions."""
        pass
