from pydantic import BaseModel, Field
from typing import Literal, Union
import datetime
from ipaddress import IPv4Address 

class SecurityEvent(BaseModel):
    """Base model for all security events, enforcing timestamp and source."""
    event_id: str
    timestamp: datetime.datetime
    source_ip: IPv4Address 

class LoginEvent(SecurityEvent):
    """Specific schema for a login event."""
    event_type: Literal['LOGIN_ATTEMPT']
    username: str
    success: bool
    
class FileChangeEvent(SecurityEvent):
    """Specific schema for a file change event."""
    event_type: Literal['FILE_CHANGE']
    file_path: str
    user_id: str

# Union type allows FastAPI to validate against *any* of these models
IngestEvent = Union[LoginEvent, FileChangeEvent]

class AnomalyReport(BaseModel):
    """Schema for the ML service to report anomalies."""
    source_ip: IPv4Address 
    score: float = Field(..., gt=0, lt=1)
    event_type: str
    timestamp: datetime.datetime
    details: dict