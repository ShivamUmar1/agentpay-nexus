import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.task import (
    TaskModel,
    TaskStepModel,
    TaskCreateRequest,
    TaskResponse,
    TaskListResponse,
    StepResponse,
)
from api.services.orchestrator import orchestration_engine
from api.services.llm_provider import AIError, AIErrorKind
from api.services.auth_session import get_current_session, verify_task_ownership
from api.services.rate_limiter import (
    enforce_task_creation_guards,
    enforce_step_advancement_guards,
    release_active_inflight,
)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def format_task_response(task: TaskModel) -> TaskResponse:
    is_unlocked = task.status in ["completed", "paid"]
    steps_formatted = []
    for s in task.steps:
        step_output = json.loads(s.output_data) if s.output_data else None
        # Server-side deliverable protection: Mask intermediate content report if not unlocked
        if not is_unlocked and s.step_name == "content_generation" and isinstance(step_output, dict):
            if "report_markdown" in step_output:
                step_output = dict(step_output)
                step_output["report_markdown"] = "[PROTECTED DELIVERABLE: Locked pending verified PayPal settlement.]"
                step_output["is_locked"] = True

        steps_formatted.append(
            StepResponse(
                id=s.id,
                task_id=s.task_id,
                step_name=s.step_name,
                assigned_agent_id=s.assigned_agent_id,
                dependencies=json.loads(s.dependencies or "[]"),
                input_data=json.loads(s.input_data) if s.input_data else None,
                output_data=step_output,
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
        execution_mode=task.execution_mode,
        execution_plan=json.loads(task.execution_plan) if task.execution_plan else None,
        final_output=json.loads(task.final_output) if (task.final_output and is_unlocked) else None,
        total_cost=task.total_cost,
        created_at=task.created_at,
        updated_at=task.updated_at,
        steps=steps_formatted
    )


@router.post("", response_model=TaskResponse)
async def create_task(
    payload: TaskCreateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Submits a new task objective and triggers multi-agent planning.
    Guarded by distributed session/IP rate limiting and active task concurrency caps.
    """
    # 1. Enforce rate limits and concurrency caps BEFORE AI planning
    enforce_task_creation_guards(request=request, db=db, session_id=session_id)

    # 2. Execute planning via multi-agent orchestrator with verified session identity
    try:
        task = await orchestration_engine.create_and_plan_task(
            db=db,
            user_id=session_id,
            title=payload.title,
            description=payload.description,
            budget=payload.budget,
            currency=payload.currency,
            constraints=payload.constraints
        )
        return format_task_response(task)
    except AIError as ai_err:
        status_code = 429 if ai_err.kind == AIErrorKind.QUOTA_EXHAUSTED else 503
        raise HTTPException(
            status_code=status_code,
            detail={
                "error_kind": ai_err.kind.value,
                "message": ai_err.user_message
            }
        )
    finally:
        release_active_inflight(db=db, session_id=session_id)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Lists tasks owned strictly by the current verified session identity."""
    query = db.query(TaskModel).filter(TaskModel.user_id == session_id)
    if status:
        query = query.filter(TaskModel.status == status)

    tasks = query.order_by(TaskModel.created_at.desc()).limit(limit).all()
    formatted = [format_task_response(t) for t in tasks]
    return TaskListResponse(tasks=formatted, total=len(formatted))


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Retrieves full details for a task. Requires verified ownership."""
    task = verify_task_ownership(task_id=task_id, session_id=session_id, db=db)
    return format_task_response(task)


@router.post("/{task_id}/advance")
async def advance_task_step(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Advances the task by 1 bounded workflow step.
    Enforces ownership, idempotent non-repetition of completed steps, parallel execution guards,
    and distributed step execution rate limiting before AI agent invocation.
    """
    # 1. Ownership check: Unauthorized callers receive 404 before rate limits or task state are touched
    task = verify_task_ownership(task_id=task_id, session_id=session_id, db=db)

    # 2. State check: do not execute AI or consume quota if task is already completed or cancelled
    if task.status in ["completed", "cancelled"]:
        return {
            "task_id": task.id,
            "status": task.status,
            "current_step": task.current_step,
            "message": "Task workflow is already completed."
        }

    # 3. Concurrency guard: prevent duplicate parallel execution of steps
    running_step = db.query(TaskStepModel).filter(
        TaskStepModel.task_id == task.id,
        TaskStepModel.status == "running"
    ).first()
    if running_step:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow step '{running_step.step_name}' is currently executing. Parallel advancement is locked."
        )

    # 4. Check whether an eligible pending step exists before consuming step rate quota
    steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task.id).all()
    step_dict = {s.step_name: s for s in steps}
    next_step: Optional[TaskStepModel] = None
    for s in steps:
        if s.status == "pending":
            deps = json.loads(s.dependencies or "[]")
            if all(step_dict.get(d) and step_dict[d].status == "completed" for d in deps):
                next_step = s
                break

    if not next_step:
        if step_dict.get("payment_approval") and step_dict["payment_approval"].status == "running":
            return {
                "task_id": task.id,
                "status": "awaiting_payment",
                "current_step": "payment_approval",
                "message": "Task is awaiting explicit user payment authorization via PayPal Checkout."
            }
        return {
            "task_id": task.id,
            "status": task.status,
            "current_step": task.current_step,
            "message": "No eligible steps to advance."
        }

    # 5. Enforce AI step advancement rate limits BEFORE executing inference
    enforce_step_advancement_guards(request=request, db=db, session_id=session_id)

    try:
        result = await orchestration_engine.advance_task(db=db, task_id=task_id)
        return result
    except AIError as ai_err:
        status_code = 429 if ai_err.kind == AIErrorKind.QUOTA_EXHAUSTED else 503
        raise HTTPException(
            status_code=status_code,
            detail={
                "error_kind": ai_err.kind.value,
                "message": ai_err.user_message,
                "task_id": task_id,
                "status": "failed"
            }
        )


@router.post("/{task_id}/cancel")
def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Cancels an in-progress or planned task. Requires verified ownership."""
    task = verify_task_ownership(task_id=task_id, session_id=session_id, db=db)

    if task.status in ["completed", "paid"]:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed or paid task.")

    task.status = "cancelled"
    db.commit()
    return {"message": "Task cancelled successfully.", "task_id": task.id}
