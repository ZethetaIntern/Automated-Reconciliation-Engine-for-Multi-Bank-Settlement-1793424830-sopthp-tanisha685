"""
Escalation Manager and SLA Compliance Monitor.
Implements the 4-tier escalation model (Auto -> Analyst -> Senior Manager -> Compliance).
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from decimal import Decimal

from backend.app.models.schemas import (
    ExceptionItem, EscalationTierEnum, SeverityLevelEnum, ExceptionStatusEnum
)


class EscalationManager:
    """
    Evaluates SLAs, routes items across the 4 escalation tiers, and detects systemic bank issues.
    """

    HIGH_VALUE_THRESHOLD = Decimal("1000000.00")  # ₹10 Lakh

    def check_sla_and_escalate(
        self,
        exceptions: List[ExceptionItem],
        current_time: datetime = None
    ) -> Tuple[List[ExceptionItem], Dict[str, Any]]:
        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        escalated_count = 0
        sla_breached_count = 0

        # Check bank frequency for systemic failure detection (> 50 exceptions in single batch)
        bank_exception_counts: Dict[str, int] = {}
        for exc in exceptions:
            if exc.status == ExceptionStatusEnum.OPEN:
                bank_exception_counts[exc.bank_code] = bank_exception_counts.get(exc.bank_code, 0) + 1

        for exc in exceptions:
            if exc.status not in (ExceptionStatusEnum.OPEN, ExceptionStatusEnum.IN_PROGRESS):
                continue

            # 1. SLA Expiry Check
            deadline = exc.sla_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if now > deadline:
                exc.is_sla_breached = True
                sla_breached_count += 1

                # Auto-escalate tier on SLA breach
                if exc.assigned_tier == EscalationTierEnum.TIER_2_ANALYST:
                    exc.assigned_tier = EscalationTierEnum.TIER_3_MANAGER
                    exc.status = ExceptionStatusEnum.ESCALATED
                    escalated_count += 1
                elif exc.assigned_tier == EscalationTierEnum.TIER_3_MANAGER:
                    exc.assigned_tier = EscalationTierEnum.TIER_4_COMPLIANCE
                    exc.status = ExceptionStatusEnum.ESCALATED
                    escalated_count += 1

            # 2. High Value Threshold Check (> ₹10 Lakh)
            try:
                amt = Decimal(exc.affected_amount)
                if amt >= self.HIGH_VALUE_THRESHOLD and exc.assigned_tier == EscalationTierEnum.TIER_2_ANALYST:
                    exc.assigned_tier = EscalationTierEnum.TIER_3_MANAGER
                    exc.severity = SeverityLevelEnum.CRITICAL
                    exc.status = ExceptionStatusEnum.ESCALATED
                    escalated_count += 1
            except Exception:
                pass

            # 3. Systemic Failure Check (>50 exceptions for single bank batch)
            if bank_exception_counts.get(exc.bank_code, 0) >= 50 and exc.assigned_tier in (EscalationTierEnum.TIER_1_AUTO, EscalationTierEnum.TIER_2_ANALYST):
                exc.assigned_tier = EscalationTierEnum.TIER_4_COMPLIANCE
                exc.status = ExceptionStatusEnum.ESCALATED
                escalated_count += 1

        metrics = {
            "total_open": len([e for e in exceptions if e.status == ExceptionStatusEnum.OPEN]),
            "sla_breached_count": sla_breached_count,
            "escalated_count": escalated_count,
            "systemic_banks": [b for b, c in bank_exception_counts.items() if c >= 50]
        }

        return exceptions, metrics
