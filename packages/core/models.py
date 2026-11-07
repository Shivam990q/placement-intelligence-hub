import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from packages.core.database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(64), unique=True, index=True, nullable=False)
    source_type = Column(String(32), nullable=False, default="company_portal") # ats_api, company_portal, telegram, rss, community
    base_url = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    check_interval_minutes = Column(Integer, default=30)
    last_checked_at = Column(DateTime, nullable=True)
    last_status = Column(String(32), default="pending") # ok, error, pending
    error_message = Column(Text, nullable=True)
    health_score = Column(Float, default=1.0)
    total_discovered = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    opportunities = relationship("Opportunity", back_populates="source", cascade="all, delete-orphan")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    external_id = Column(String(128), index=True, nullable=True)
    company = Column(String(128), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    normalized_title = Column(String(256), index=True, nullable=False)
    role_category = Column(String(64), default="full_time", index=True) # internship, full_time, mass_hiring, genai_ops, resource
    
    locations = Column(JSON, default=list) # ["Bengaluru", "Remote"]
    eligible_batches = Column(JSON, default=list) # ["2026", "2027"]
    eligible_degrees = Column(JSON, default=list) # ["B.Tech", "MCA"]
    eligible_branches = Column(JSON, default=list) # ["CS", "IT", "EC"]
    
    ctc_min = Column(Float, nullable=True)
    ctc_max = Column(Float, nullable=True)
    ctc_currency = Column(String(16), default="INR")
    ctc_text = Column(String(128), nullable=True) # e.g. "₹6 - 8 LPA"
    
    apply_url = Column(String(1024), nullable=False)
    canonical_url_hash = Column(String(64), index=True, nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)
    
    raw_description = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    requirements = Column(JSON, default=list) # ["DSA", "Python", "RLHF"]
    deadline = Column(String(128), nullable=True)
    
    status = Column(String(32), default="pending_approval", index=True) # discovered, pending_approval, approved, rejected, published, expired
    confidence_score = Column(Float, default=1.0)
    verification_status = Column(String(32), default="verified_official", index=True) # verified_official, verified_secondary, unverified
    verification_evidence = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    source = relationship("Source", back_populates="opportunities")
    versions = relationship("OpportunityVersion", back_populates="opportunity", cascade="all, delete-orphan")
    approvals = relationship("ApprovalQueue", back_populates="opportunity", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="opportunity", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_opp_company_title", "company", "normalized_title"),
    )


class OpportunityVersion(Base):
    __tablename__ = "opportunity_versions"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    version_num = Column(Integer, default=1)
    snapshot_data = Column(JSON, nullable=False)
    change_summary = Column(String(256), nullable=True)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    opportunity = relationship("Opportunity", back_populates="versions")


class ApprovalQueue(Base):
    __tablename__ = "approval_queue"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False, index=True)
    status = Column(String(32), default="pending", index=True) # pending, approved, rejected, edited
    reviewed_by = Column(String(64), nullable=True)
    feedback = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    opportunity = relationship("Opportunity", back_populates="approvals")


class Publication(Base):
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    platform = Column(String(32), nullable=False) # telegram_channel, telegram_topic, whatsapp_clipboard
    destination_id = Column(String(128), nullable=True)
    message_id = Column(String(64), nullable=True)
    status = Column(String(32), default="sent") # sent, pending, failed
    formatted_content = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    published_at = Column(DateTime, default=datetime.datetime.utcnow)

    opportunity = relationship("Opportunity", back_populates="publications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=True)
    actor = Column(String(64), default="system")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
