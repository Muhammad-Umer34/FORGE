# D:\FYP\FORGE-1\backend\models\session.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MessageRecord(BaseModel):
    role: str = Field(..., description="Role: 'human', 'ai', or 'system'")
    content: str = Field(..., description="Message text")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    session_id: str
    messages: List[MessageRecord] = Field(default_factory=list)
    turn_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
