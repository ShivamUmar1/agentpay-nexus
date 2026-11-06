import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.database import get_db
from api.models.agent import AgentModel, AgentResponse, AgentListResponse

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("", response_model=AgentListResponse)
def list_agents(
    category: Optional[str] = None,
    search: Optional[str] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("rating"),
    db: Session = Depends(get_db)
):
    """Discovers and filters specialized AI agents from the registered marketplace."""
    query = db.query(AgentModel)

    if category and category != "All":
        query = query.filter(AgentModel.category == category)

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                AgentModel.name.ilike(search_fmt),
                AgentModel.description.ilike(search_fmt),
                AgentModel.capabilities.ilike(search_fmt)
            )
        )

    if max_price is not None:
        query = query.filter(AgentModel.price <= max_price)

    if sort_by == "rating":
        query = query.order_by(AgentModel.rating.desc())
    elif sort_by == "price_asc":
        query = query.order_by(AgentModel.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(AgentModel.price.desc())
    elif sort_by == "completed_tasks":
        query = query.order_by(AgentModel.completed_tasks.desc())

    agents = query.all()
    
    # Format JSON strings to Python lists
    formatted = []
    for a in agents:
        formatted.append(
            AgentResponse(
                id=a.id,
                name=a.name,
                description=a.description,
                category=a.category,
                capabilities=json.loads(a.capabilities or "[]"),
                supported_tasks=json.loads(a.supported_tasks or "[]"),
                pricing_model=a.pricing_model,
                price=a.price,
                currency=a.currency,
                availability=a.availability,
                rating=a.rating,
                completed_tasks=a.completed_tasks,
                icon=a.icon,
                estimated_time=a.estimated_time
            )
        )

    return AgentListResponse(agents=formatted, total=len(formatted))


@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db)):
    """Retrieves all unique agent categories."""
    categories = db.query(AgentModel.category).distinct().all()
    return [c[0] for c in categories if c[0]]


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Retrieves full profile and performance metrics for a specific agent."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        category=agent.category,
        capabilities=json.loads(agent.capabilities or "[]"),
        supported_tasks=json.loads(agent.supported_tasks or "[]"),
        pricing_model=agent.pricing_model,
        price=agent.price,
        currency=agent.currency,
        availability=agent.availability,
        rating=agent.rating,
        completed_tasks=agent.completed_tasks,
        icon=agent.icon,
        estimated_time=agent.estimated_time
    )
