import os
import time
from contextlib import contextmanager
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from api.config import settings

# Adjust URL if needed (e.g. postgres:// to postgresql://)
db_url = settings.DATABASE_URL.strip() if settings.DATABASE_URL else ""
if not db_url:
    db_url = "sqlite:///./agentpay.db"
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
engine_kwargs: Dict[str, Any] = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # If running in Vercel or container with read-only root, use /tmp
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(".", os.W_OK):
        db_url = "sqlite:////tmp/agentpay.db"
else:
    # Serverless-friendly PostgreSQL connection pooling (for Supabase session/transaction pooler)
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_timeout": 30
    })

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

# Enable foreign keys for SQLite
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for service layer usage."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initializes database tables and seeds default marketplace agents if missing."""
    Base.metadata.create_all(bind=engine)
    from api.seed_data import seed_marketplace_agents
    with get_db_context() as db:
        seed_marketplace_agents(db)


def test_db_connection() -> Dict[str, Any]:
    """Performs a live diagnostic check of the database connection."""
    t0 = time.time()
    is_postgres = "postgres" in db_url
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
            # Count records
            from api.models.agent import AgentModel
            from api.models.task import TaskModel
            from api.models.payment import TransactionModel
            
            agent_count = db.query(AgentModel).count()
            task_count = db.query(TaskModel).count()
            tx_count = db.query(TransactionModel).count()
            latency = round((time.time() - t0) * 1000, 1)

            return {
                "status": "connected",
                "type": "postgresql" if is_postgres else "sqlite",
                "hosted": "supabase" if "supabase" in db_url else ("hosted_postgresql" if is_postgres else "local_sqlite"),
                "persistent": is_postgres,
                "latency_ms": latency,
                "counts": {
                    "agents": agent_count,
                    "tasks": task_count,
                    "transactions": tx_count
                }
            }
    except Exception as e:
        return {
            "status": "error",
            "type": "postgresql" if is_postgres else "sqlite",
            "persistent": is_postgres,
            "error": str(e)
        }
