from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class SourceBase(BaseModel):
    name: str = Field(...)
    slug: str = Field(...)
    source_type: str = Field(default="company_portal")
    base_url: str = Field(...)
    is_active: bool = True
    check_interval_minutes: int = 15

class SourceCreate(SourceBase):
    pass

class SourceResponse(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_checked_at: Optional[datetime] = None
    last_status: str
    error_message: Optional[str] = None
    health_score: float
    total_discovered: int
    created_at: datetime
