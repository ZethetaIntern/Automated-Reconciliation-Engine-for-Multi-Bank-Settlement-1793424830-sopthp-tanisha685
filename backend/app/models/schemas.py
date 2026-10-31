"""
Pydantic Schemas, Enums, and Request/Response Models.
Defines all 18 Exception Categories, Match Types, Severity Levels, Escalation Tiers.
"""

from decimal import Decimal
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MatchTypeEnum(str, Enum):
    EXACT = "EXACT"
    FUZZY = "FUZZY"
    RULE = "RULE"
    SPLIT = "SPLIT"
    NETTED = "NETTED"
    MANUAL = "MANUAL"
    UNMATCHED = "UNMATCHED"


class ExceptionCategoryEnum(str, Enum):
    """The 18 reconciliation exception categories defined in Section A4.1."""
    MISSING_INTERNAL = "MISSING_INTERNAL"
    MISSING_EXTERNAL = "MISSING_EXTERNAL"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DUPLICATE_INTERNAL = "DUPLICATE_INTERNAL"
    DUPLICATE_EXTERNAL = "DUPLICATE_EXTERNAL"
    DATE_MISMATCH = "DATE_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    DIRECTION_REVERSAL = "DIRECTION_REVERSAL"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NETTED_SETTLEMENT = "NETTED_SETTLEMENT"
    FEE_DEDUCTION = "FEE_DEDUCTION"
    FX_VARIANCE = "FX_VARIANCE"
    STALE_TRANSACTION = "STALE_TRANSACTION"
    FORMAT_ERROR = "FORMAT_ERROR"
    REFERENCE_TRUNCATED = "REFERENCE_TRUNCATED"
    TIMEZONE_OFFSET = "TIMEZONE_OFFSET"
    REVERSAL_PENDING = "REVERSAL_PENDING"
    REGULATORY_HOLD = "REGULATORY_HOLD"
    # Bonus from RBI Clause 8.2
    SETTLEMENT_DELAY = "SETTLEMENT_DELAY"


class SeverityLevelEnum(str, Enum):
    CRITICAL = "CRITICAL"  # Financial loss > ₹10L or direction reversal
    HIGH = "HIGH"          # SLA < 2 hours
    MEDIUM = "MEDIUM"      # SLA 2-8 hours
    LOW = "LOW"            # SLA > 8 hours


class EscalationTierEnum(str, Enum):
    TIER_1_AUTO = "TIER_1_AUTO"                # Auto-resolution
    TIER_2_ANALYST = "TIER_2_ANALYST"          # Operations Analyst
    TIER_3_MANAGER = "TIER_3_MANAGER"          # Senior Ops Manager (> ₹10L or >4h breach)
    TIER_4_COMPLIANCE = "TIER_4_COMPLIANCE"    # Compliance / Risk / FIU-IND


class ExceptionStatusEnum(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    VOIDED = "VOIDED"
    AUTO_RESOLVED = "AUTO_RESOLVED"


class RunStatusEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Request / Response Schemas
class ReconciliationRunRequest(BaseModel):
    bank_code: str = Field(..., description="Target bank (e.g. HDFC, ICICI, AXIS, SBI, KOTAK, ALL)")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    fast_mode: bool = Field(default=False, description="Fast mode: runs exact match only for emergency backlog clearing")
    tolerance_amount: Decimal = Field(default=Decimal("0.01"), description="Amount tolerance for same-currency")
    tolerance_fx: Decimal = Field(default=Decimal("0.015"), description="FX tolerance threshold (1.5%)")
    date_offset_days: int = Field(default=1, description="Max allowable settlement date offset")


class MatchResultItem(BaseModel):
    match_id: str
    run_id: str
    internal_txn_id: Optional[str] = None
    external_txn_id: Optional[str] = None
    internal_txn_ids: Optional[List[str]] = Field(default_factory=list)
    external_txn_ids: Optional[List[str]] = Field(default_factory=list)
    match_type: MatchTypeEnum
    confidence_score: float
    rule_name: Optional[str] = None
    internal_amount: Optional[str] = None
    external_amount: Optional[str] = None
    amount_diff: Optional[str] = None
    bank_code: str
    matched_at: datetime
    breakdown: Optional[Dict[str, float]] = Field(default_factory=dict)


class ExceptionItem(BaseModel):
    exception_id: str
    run_id: str
    category: ExceptionCategoryEnum
    severity: SeverityLevelEnum
    status: ExceptionStatusEnum
    assigned_tier: EscalationTierEnum
    bank_code: str
    internal_txn_id: Optional[str] = None
    external_txn_id: Optional[str] = None
    affected_amount: str
    currency: str
    description: str
    suggested_resolution: str
    resolution_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    sla_minutes: int
    created_at: datetime
    sla_deadline: datetime
    is_sla_breached: bool = False
    auto_resolvable: bool = False


class ResolveExceptionRequest(BaseModel):
    resolution_action: str = Field(..., description="e.g. VOID_DUPLICATE, MANUAL_MATCH, WRITE_OFF, ADJUST_FEE, ESCALATE_COMPLIANCE")
    resolution_notes: str = Field(..., min_length=3, description="Audit justification for exception resolution")
    resolved_by: str = Field(default="ops_analyst_1", description="User ID / Actor")
    target_match_id: Optional[str] = None


class AuditLogItem(BaseModel):
    event_id: str
    timestamp: datetime
    actor: str
    action_type: str
    affected_records: List[str]
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    rationale: str
    sha256_hash: str
    prev_hash: str
    is_valid: Optional[bool] = True


class DashboardSummaryResponse(BaseModel):
    total_internal_transactions: int
    total_external_transactions: int
    matched_count: int
    overall_match_rate: float
    exact_match_rate: float
    fuzzy_match_rate: float
    rule_match_rate: float
    unmatched_count: int
    total_exceptions: int
    open_exceptions: int
    auto_resolved_exceptions: int
    critical_exceptions: int
    sla_compliance_rate: float
    avg_processing_time_ms: float
    exceptions_by_category: Dict[str, int]
    exceptions_by_severity: Dict[str, int]
    bank_breakdown: List[Dict[str, Any]]
    active_anomalies: List[Dict[str, Any]]
    audit_chain_valid: bool
    total_reconciled_value_inr: str
    total_variance_value_inr: str
