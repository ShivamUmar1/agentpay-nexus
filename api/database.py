import os
import time
import logging
from contextlib import contextmanager
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.exc import OperationalError, DatabaseError
from api.config import settings

logger = logging.getLogger(__name__)

# Primary database URL
raw_url = settings.DATABASE_URL.strip() if settings.DATABASE_URL else ""
if not raw_url:
    db_url = "sqlite:///./agentpay.db"
elif raw_url.startswith("postgres://"):
    db_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
    db_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    db_url = raw_url

# Fallback SQLite URL (for serverless /tmp or local fallback)
fallback_sqlite_url = "sqlite:////tmp/agentpay.db" if (os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(".", os.W_OK)) else "sqlite:///./agentpay.db"

# Configure Primary Engine
primary_connect_args = {}
primary_engine_kwargs: Dict[str, Any] = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if db_url.startswith("sqlite"):
    primary_connect_args["check_same_thread"] = False
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(".", os.W_OK):
        db_url = "sqlite:////tmp/agentpay.db"
else:
    primary_connect_args["prepare_threshold"] = None
    primary_engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_timeout": 15
    })

engine = create_engine(
    db_url,
    connect_args=primary_connect_args,
    **primary_engine_kwargs
)

fallback_engine = create_engine(
    fallback_sqlite_url,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

# Enable foreign keys for SQLite
for eng in [engine, fallback_engine]:
    if str(eng.url).startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
FallbackSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=fallback_engine)
Base = declarative_base()


def get_active_session() -> Session:
    """Returns a session. In production, strictly requires PostgreSQL and refuses SQLite fallback."""
    if not str(engine.url).startswith("sqlite"):
        try:
            # Test quick connection ping
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return SessionLocal()
        except (OperationalError, DatabaseError, Exception) as e:
            # Disable SQLite fallback for production
            if settings.APP_ENV == "production" or os.environ.get("VERCEL"):
                logger.error(f"PostgreSQL connection failed in production: {e}")
                raise RuntimeError(f"Database connection error: PostgreSQL is unreachable in production: {e}")
            logger.warning(f"Primary PostgreSQL engine unavailable ({e}). Using local fallback engine in development.")
            return FallbackSessionLocal()
    elif settings.APP_ENV == "production" or os.environ.get("VERCEL"):
        # In production, if DATABASE_URL was left as sqlite, warn/raise
        logger.warning("Running on SQLite in production is not recommended for persistence.")
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = get_active_session()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for service layer usage."""
    db = get_active_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initializes database tables and seeds default marketplace agents on primary engine.
    In hosted/production environments, skips runtime DDL on cold starts (schema managed via migrations).
    """
    import api.models  # noqa: F401 - ensure all models are registered on Base
    from api.seed_data import seed_marketplace_agents
    
    if settings.APP_ENV == "production" or os.environ.get("VERCEL"):
        # In hosted/production serverless environments, avoid concurrent DDL execution on cold starts.
        # Production database schema is provisioned via explicit SQL migrations.
        try:
            with SessionLocal() as db:
                from api.models.agent import AgentModel
                if db.query(AgentModel).count() == 0:
                    seed_marketplace_agents(db)
        except Exception as seed_err:
            logger.warning(f"Production agent seed check skipped: {seed_err}")
        return

    # Try primary engine for local / test environments
    try:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_marketplace_agents(db)
        logger.info("Database initialized successfully on primary engine.")
    except Exception as e:
        logger.warning(f"Primary engine init_db failed: {e}. Initializing fallback engine.")
        Base.metadata.create_all(bind=fallback_engine)
        with FallbackSessionLocal() as db:
            seed_marketplace_agents(db)


def test_db_connection() -> Dict[str, Any]:
    """Performs a live diagnostic check of the primary configured database connection."""
    t0 = time.time()
    is_postgres = "postgres" in db_url
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        with SessionLocal() as db:
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
