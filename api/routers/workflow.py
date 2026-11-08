import json
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.task import TaskStepModel
from api.models.log import ActivityLogModel, ActivityLogResponse
from api.services.auth_session import get_current_session, verify_task_ownership

router = APIRouter(prefix="/api/tasks/{task_id}", tags=["Workflow"])


@router.get("/progress")
def get_task_progress(
    task_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Retrieves execution progress and node dependencies for the visual workflow. Requires verified ownership."""
    task = verify_task_ownership(task_id=task_id, session_id=session_id, db=db)

    steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task_id).all()
    total_steps = len(steps)
    completed_steps = sum(1 for s in steps if s.status == "completed")
    progress_pct = int((completed_steps / total_steps * 100)) if total_steps > 0 else 0

    return {
        "task_id": task.id,
        "title": task.title,
        "status": task.status,
        "current_step": task.current_step,
        "progress_percentage": progress_pct,
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "total_cost": task.total_cost,
        "budget": task.budget,
        "steps": [
            {
                "id": s.id,
                "step_name": s.step_name,
                "assigned_agent_id": s.assigned_agent_id,
                "status": s.status,
                "dependencies": json.loads(s.dependencies or "[]"),
                "started_at": s.started_at,
                "completed_at": s.completed_at
            }
            for s in steps
        ]
    }


@router.get("/activity", response_model=List[ActivityLogResponse])
def get_task_activity(
    task_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Retrieves real-time execution activity logs for this task. Requires verified ownership."""
    verify_task_ownership(task_id=task_id, session_id=session_id, db=db)

    logs = (
        db.query(ActivityLogModel)
        .filter(ActivityLogModel.task_id == task_id)
        .order_by(ActivityLogModel.created_at.desc())
        .limit(limit)
        .all()
    )
    return logs


@router.get("/results")
def get_task_results(
    task_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session)
):
    """Retrieves verified deliverables and final report if unlocked. Requires verified ownership."""
    task = verify_task_ownership(task_id=task_id, session_id=session_id, db=db)

    is_unlocked = task.status in ["completed", "paid"]

    return {
        "task_id": task.id,
        "title": task.title,
        "status": task.status,
        "is_unlocked": is_unlocked,
        "total_cost": task.total_cost,
        "currency": task.currency,
        "deliverables": json.loads(task.final_output) if is_unlocked and task.final_output else None
    }
