"""
Database Models and Storage Layer using SQLAlchemy.
Implements the 8 required tables with indexing, constraints, and audit chaining.
"""

import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime,
    Date, Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reconciliation_engine.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utcnow_func():
    return datetime.now(timezone.utc)


class RawTransaction(Base):
    __tablename__ = "raw_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_id = Column(String(128), index=True)
    source_format = Column(String(32), index=True)  # CSV, MT940, CAMT.053
    source_file = Column(String(255), index=True)
    bank_code = Column(String(32), index=True)
    file_sha256 = Column(String(64), index=True)
    raw_content = Column(JSON)
    ingested_at = Column(DateTime, default=utcnow_func, index=True)


class NormalisedTransaction(Base):
    __tablename__ = "normalised_transactions"

    txn_id = Column(String(64), primary_key=True, index=True)
    txn_date = Column(DateTime, nullable=False, index=True)
    amount = Column(String(32), nullable=False)  # Decimal formatted string
    amount_numeric = Column(Float, nullable=False, index=True)
    currency = Column(String(3), nullable=False, index=True)
    direction = Column(String(2), nullable=False, index=True)  # CR / DR
    counterparty_name = Column(String(140), index=True)
    counterparty_account = Column(String(34))
    bank_ref = Column(String(64), index=True)
    narration = Column(String(500))
    settlement_date = Column(Date, nullable=True, index=True)
    source_format = Column(String(32))
    source_file = Column(String(255))
    bank_code = Column(String(32), index=True)
    is_masked = Column(Boolean, default=False)
    ingested_at = Column(DateTime, default=utcnow_func)

    __table_args__ = (
        Index("idx_norm_lookup", "bank_code", "currency", "direction", "amount_numeric"),
    )


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    run_id = Column(String(64), primary_key=True, index=True)
    bank_code = Column(String(32), index=True)
    status = Column(String(32), default="PENDING")
    fast_mode = Column(Boolean, default=False)
    total_internal = Column(Integer, default=0)
    total_external = Column(Integer, default=0)
    matched_count = Column(Integer, default=0)
    exact_matches = Column(Integer, default=0)
    fuzzy_matches = Column(Integer, default=0)
    rule_matches = Column(Integer, default=0)
    split_matches = Column(Integer, default=0)
    netted_matches = Column(Integer, default=0)
    exception_count = Column(Integer, default=0)
    auto_resolved_count = Column(Integer, default=0)
    match_rate = Column(Float, default=0.0)
    duration_ms = Column(Float, default=0.0)
    opening_balance = Column(String(32), default="0.00")
    closing_balance = Column(String(32), default="0.00")
    computed_closing_balance = Column(String(32), default="0.00")
    balance_reconciled = Column(Boolean, default=True)
    started_at = Column(DateTime, default=utcnow_func)
    completed_at = Column(DateTime, nullable=True)


class MatchResult(Base):
    __tablename__ = "match_results"

    match_id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("reconciliation_runs.run_id"), index=True)
    internal_txn_id = Column(String(64), nullable=True, index=True)
    external_txn_id = Column(String(64), nullable=True, index=True)
    internal_txn_ids_json = Column(JSON, nullable=True)  # for split/netting
    external_txn_ids_json = Column(JSON, nullable=True)
    match_type = Column(String(32), index=True)  # EXACT, FUZZY, RULE, SPLIT, NETTED
    confidence_score = Column(Float, nullable=False, index=True)
    rule_name = Column(String(64), nullable=True)
    internal_amount = Column(String(32))
    external_amount = Column(String(32))
    amount_diff = Column(String(32), default="0.00")
    bank_code = Column(String(32), index=True)
    breakdown_json = Column(JSON, default=dict)
    matched_at = Column(DateTime, default=utcnow_func)


class ReconciliationException(Base):
    __tablename__ = "exceptions"

    exception_id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey("reconciliation_runs.run_id"), index=True)
    category = Column(String(64), nullable=False, index=True)  # The 18 categories
    severity = Column(String(32), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(32), default="OPEN", index=True)    # OPEN, RESOLVED, ESCALATED, etc.
    assigned_tier = Column(String(32), default="TIER_2_ANALYST")
    bank_code = Column(String(32), index=True)
    internal_txn_id = Column(String(64), nullable=True, index=True)
    external_txn_id = Column(String(64), nullable=True, index=True)
    affected_amount = Column(String(32), default="0.00")
    currency = Column(String(3), default="INR")
    description = Column(Text)
    suggested_resolution = Column(Text)
    resolution_action = Column(String(64), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    sla_minutes = Column(Integer, default=240)
    created_at = Column(DateTime, default=utcnow_func, index=True)
    sla_deadline = Column(DateTime, nullable=False)
    auto_resolvable = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    event_id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(DateTime, default=utcnow_func, index=True)
    actor = Column(String(64), nullable=False, index=True)
    action_type = Column(String(64), nullable=False, index=True)  # INGEST, NORMALISE, MATCH, UNMATCH, RESOLVE, ESCALATE, OVERRIDE
    affected_records = Column(JSON)  # List of transaction IDs
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    rationale = Column(Text)
    prev_hash = Column(String(64), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)


class BankConfiguration(Base):
    __tablename__ = "bank_configurations"

    bank_code = Column(String(32), primary_key=True)
    bank_name = Column(String(128), nullable=False)
    supported_formats = Column(JSON)  # ["CSV", "MT940", "CAMT.053"]
    timezone = Column(String(64), default="Asia/Kolkata")
    settlement_cycle = Column(String(32), default="T+1")
    reconciliation_window_days = Column(Integer, default=5)
    column_mappings = Column(JSON, nullable=True)
    mt940_deviations = Column(JSON, nullable=True)
    tolerance_amount = Column(Float, default=0.01)
    tolerance_fx = Column(Float, default=0.015)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=utcnow_func)


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, index=True)
    full_name = Column(String(128))
    role = Column(String(32), default="ANALYST")  # VIEWER, ANALYST, ADMIN, SYSTEM
    email = Column(String(128))
    api_key = Column(String(128), unique=True)
    is_active = Column(Boolean, default=True)


def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for obtaining DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
