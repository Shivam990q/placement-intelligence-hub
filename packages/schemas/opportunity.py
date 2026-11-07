from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class OpportunityBase(BaseModel):
    company: str = Field(...)
    title: str = Field(...)
    role_category: str = Field(default="full_time")
    locations: List[str] = Field(default_factory=list)
    eligible_batches: List[str] = Field(default_factory=list)
    eligible_degrees: List[str] = Field(default_factory=list)
    eligible_branches: List[str] = Field(default_factory=list)
    ctc_min: Optional[float] = None
    ctc_max: Optional[float] = None
    ctc_currency: str = "INR"
    ctc_text: Optional[str] = None
    apply_url: str = Field(...)
    raw_description: Optional[str] = None
    summary: Optional[str] = None
    requirements: List[str] = Field(default_factory=list)
    deadline: Optional[str] = None

class OpportunityCreate(OpportunityBase):
    source_id: Optional[int] = None
    external_id: Optional[str] = None
    status: str = "pending_approval"
    confidence_score: float = 1.0
    verification_status: str = "verified_official"
    verification_evidence: Dict[str, Any] = Field(default_factory=dict)

class OpportunityUpdate(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    role_category: Optional[str] = None
    locations: Optional[List[str]] = None
    eligible_batches: Optional[List[str]] = None
    eligible_degrees: Optional[List[str]] = None
    eligible_branches: Optional[List[str]] = None
    ctc_text: Optional[str] = None
    apply_url: Optional[str] = None
    requirements: Optional[List[str]] = None
    deadline: Optional[str] = None
    status: Optional[str] = None

class OpportunityResponse(OpportunityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: Optional[int] = None
    external_id: Optional[str] = None
    normalized_title: str
    status: str
    confidence_score: float
    verification_status: str
    verification_evidence: Dict[str, Any]
    canonical_url_hash: str
    created_at: datetime
    updated_at: datetime

class OpportunityFilter(BaseModel):
    search: Optional[str] = None
    batch: Optional[str] = None
    role_category: Optional[str] = None
    status: Optional[str] = None
    verification_status: Optional[str] = None
    limit: int = 50
    offset: int = 0
