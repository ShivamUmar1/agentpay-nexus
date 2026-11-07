from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict
from api.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    budget = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    status = Column(String(32), default="planning", index=True)
    current_step = Column(String(64), default="planning")
    execution_plan = Column(Text, nullable=True)  # JSON serialized plan
    final_output = Column(Text, nullable=True)    # JSON serialized deliverables
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = relationship("TaskStepModel", back_populates="task", cascade="all, delete-orphan", order_by="TaskStepModel.started_at")
    runs = relationship("AgentRunModel", back_populates="task", cascade="all, delete-orphan")

    @property
    def execution_mode(self) -> str:
        """Determines whether task was executed with live AI or in offline scaffold mode."""
        if self.execution_plan:
            try:
                import json
                p = json.loads(self.execution_plan)
                if isinstance(p, dict) and "execution_mode" in p:
                    return p["execution_mode"]
            except Exception:
                pass
        return "live_ai"


class TaskStepModel(Base):
    __tablename__ = "task_steps"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(64), nullable=False)
    assigned_agent_id = Column(String(64), nullable=True)
    dependencies = Column(Text, nullable=True)   # JSON array of step_names
    input_data = Column(Text, nullable=True)     # JSON string
    output_data = Column(Text, nullable=True)    # JSON string
    status = Column(String(32), default="pending")  # pending, running, completed, failed, skipped
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("TaskModel", back_populates="steps")


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="running")  # running, completed, failed
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    execution_metadata = Column(Text, nullable=True)  # token count, cost, timing
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("TaskModel", back_populates="runs")


# Pydantic Schemas
class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=256)
    description: str = Field(..., min_length=10)
    budget: float = Field(..., gt=0)
    currency: str = "USD"
    constraints: Optional[str] = None
    expected_deliverables: Optional[str] = None


class StepResponse(BaseModel):
    id: str
    task_id: str
    step_name: str
    assigned_agent_id: Optional[str] = None
    dependencies: Optional[List[str]] = None
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentRunResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    status: str
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    execution_metadata: Optional[Any] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    budget: float
    currency: str
    status: str
    current_step: str
    execution_mode: str = "live_ai"
    execution_plan: Optional[Any] = None
    final_output: Optional[Any] = None
    total_cost: float
    created_at: datetime
    updated_at: datetime
    steps: List[StepResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
