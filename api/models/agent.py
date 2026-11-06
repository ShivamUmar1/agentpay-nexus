from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import Column, String, Float, Integer, Text, DateTime
from pydantic import BaseModel, ConfigDict
from api.database import Base


class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, index=True)
    capabilities = Column(Text, nullable=False)  # JSON string or comma-separated
    supported_tasks = Column(Text, nullable=False)  # JSON string
    pricing_model = Column(String(32), default="fixed_per_task")
    price = Column(Float, default=0.0)
    currency = Column(String(8), default="USD")
    availability = Column(String(32), default="available")  # available, busy, offline
    rating = Column(Float, default=5.0)
    completed_tasks = Column(Integer, default=0)
    icon = Column(String(64), default="Bot")
    estimated_time = Column(String(64), default="1-2 min")
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas
class AgentBase(BaseModel):
    id: str
    name: str
    description: str
    category: str
    capabilities: List[str]
    supported_tasks: List[str]
    pricing_model: str = "fixed_per_task"
    price: float = 0.0
    currency: str = "USD"
    availability: str = "available"
    rating: float = 5.0
    completed_tasks: int = 0
    icon: str = "Bot"
    estimated_time: str = "1-2 min"


class AgentResponse(AgentBase):
    model_config = ConfigDict(from_attributes=True)


class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int
