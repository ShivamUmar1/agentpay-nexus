import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.task import TaskModel, TaskStepModel
from api.models.log import ActivityLogModel, ActivityLogResponse

router = APIRouter(prefix="/api/tasks/{task_id}", tags=["Workflow"])


@router.get("/progress")
def get_task_progress(task_id: str, db: Session = Depends(get_db)):
    """Retrieves execution progress and node dependencies for the visual workflow."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

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
def get_task_activity(task_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieves real-time execution activity logs for this task."""
    logs = (
        db.query(ActivityLogModel)
        .filter(ActivityLogModel.task_id == task_id)
        .order_by(ActivityLogModel.created_at.desc())
        .limit(limit)
        .all()
    )
    return logs


@router.get("/results")
def get_task_results(task_id: str, db: Session = Depends(get_db)):
    """Retrieves verified deliverables and final report if unlocked."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    is_unlocked = task.status == "completed" or (task.final_output is not None)
    
    return {
        "task_id": task.id,
        "title": task.title,
        "status": task.status,
        "is_unlocked": is_unlocked,
        "total_cost": task.total_cost,
        "currency": task.currency,
        "deliverables": json.loads(task.final_output) if is_unlocked and task.final_output else None
    }
