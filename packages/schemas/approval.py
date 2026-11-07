from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from packages.schemas.opportunity import OpportunityResponse

class ApprovalActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|edit)$")
    reviewed_by: str = Field(default="admin")
    feedback: Optional[str] = None
    edited_data: Optional[Dict[str, Any]] = None
    publish_telegram: bool = True
    telegram_target: str = Field(default="both") # channel, topic, both

class ApprovalQueueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    opportunity_id: int
    status: str
    reviewed_by: Optional[str] = None
    feedback: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    opportunity: Optional[OpportunityResponse] = None
