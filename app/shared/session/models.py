from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionData(BaseModel):
    user_id: str
    token_id: str
    refresh_token: str
    email: str
    account_type: str
    is_master: bool
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class SessionTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserData(BaseModel):
    user_id: str
    email: str
    account_type: str
    is_master: bool
    token_id: Optional[str] = None


class RateLimitInfo(BaseModel):
    ip_address: str
    attempts: int
    blocked_until: Optional[datetime] = None
