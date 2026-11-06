from datetime import datetime
import uuid
from typing import Optional, Any
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from pydantic import BaseModel, ConfigDict
from api.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class ActivityLogModel(Base):
    __tablename__ = "activity_logs"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)  # system, plan, delegate, execute, review, payment, error
    message = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ActivityLogResponse(BaseModel):
    id: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    event_type: str
    message: str
    metadata_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
