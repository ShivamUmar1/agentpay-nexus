import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.task import TaskModel, TaskStepModel, TaskCreateRequest, TaskResponse, TaskListResponse, StepResponse
from api.services.orchestrator import orchestration_engine

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extracts user ID from Supabase JWT or defaults to guest/demo user."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        # In full Supabase auth setup, verify JWT; for demo/hackathon fallback to sub or token prefix
        return "user_auth_demo"
    return "user_guest_01"


def format_task_response(task: TaskModel) -> TaskResponse:
    steps_formatted = []
    for s in task.steps:
        steps_formatted.append(
            StepResponse(
                id=s.id,
                task_id=s.task_id,
                step_name=s.step_name,
                assigned_agent_id=s.assigned_agent_id,
                dependencies=json.loads(s.dependencies or "[]"),
                input_data=json.loads(s.input_data) if s.input_data else None,
                output_data=json.loads(s.output_data) if s.output_data else None,
                status=s.status,
                error_message=s.error_message,
                started_at=s.started_at,
                completed_at=s.completed_at
            )
        )

    return TaskResponse(
        id=task.id,
        user_id=task.user_id,
        title=task.title,
        description=task.description,
        budget=task.budget,
        currency=task.currency,
        status=task.status,
        current_step=task.current_step,
        execution_plan=json.loads(task.execution_plan) if task.execution_plan else None,
        final_output=json.loads(task.final_output) if task.final_output else None,
        total_cost=task.total_cost,
        created_at=task.created_at,
        updated_at=task.updated_at,
        steps=steps_formatted
    )


@router.post("", response_model=TaskResponse)
async def create_task(
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Submits a new task objective and triggers multi-agent planning."""
    task = await orchestration_engine.create_and_plan_task(
        db=db,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        budget=payload.budget,
        currency=payload.currency,
        constraints=payload.constraints
    )
    return format_task_response(task)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Lists tasks for the current authenticated user."""
    query = db.query(TaskModel).filter(TaskModel.user_id == user_id)
    if status:
        query = query.filter(TaskModel.status == status)

    tasks = query.order_by(TaskModel.created_at.desc()).limit(limit).all()
    formatted = [format_task_response(t) for t in tasks]
    return TaskListResponse(tasks=formatted, total=len(formatted))


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves full details, execution plan, and subtask steps for a task."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return format_task_response(task)


@router.post("/{task_id}/advance")
async def advance_task_step(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Advances the task by 1 bounded workflow step (Vercel serverless friendly)."""
    result = await orchestration_engine.advance_task(db=db, task_id=task_id)
    return result


@router.post("/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Cancels an in-progress or planned task."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task.status in ["completed", "paid"]:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed or paid task.")

    task.status = "cancelled"
    db.commit()
    return {"message": "Task cancelled successfully.", "task_id": task.id}
