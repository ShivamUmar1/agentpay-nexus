import hashlib
import ipaddress
import logging
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from fastapi import Request, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from api.config import settings
from api.models.ratelimit import RateLimitRecord
from api.models.task import TaskModel

logger = logging.getLogger(__name__)


def get_current_time() -> datetime:
    """Returns the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class RateLimiterUnavailableError(Exception):
    """Raised when the rate limiting storage/database is unreachable."""
    pass


def _validate_ip_address(candidate: Optional[str]) -> Optional[str]:
    """Validates and normalizes an IP candidate using python ipaddress module."""
    if not candidate or not candidate.strip():
        return None
    cleaned = candidate.strip().strip("[]")
    if ":" in cleaned and "." in cleaned:
        cleaned = cleaned.split(":")[0].strip()
    try:
        addr = ipaddress.ip_address(cleaned)
        return addr.compressed
    except ValueError:
        return None


def extract_client_ip(request: Request) -> str:
    """Safely extracts and normalizes client IP address.

    In hosted environments (Vercel), prioritizes Vercel-verified proxy headers (x-real-ip, x-forwarded-for).
    In local / non-hosted environments, client-supplied proxy headers are untrusted to prevent forgery,
    so request.client.host is used directly.
    """
    if settings.is_hosted:
        # 1. Trusted Vercel client IP header
        real_ip = request.headers.get("x-real-ip")
        valid_real = _validate_ip_address(real_ip)
        if valid_real:
            return valid_real

        # 2. Leftmost token in x-forwarded-for
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded and forwarded.strip():
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                valid_fwd = _validate_ip_address(parts[0])
                if valid_fwd:
                    return valid_fwd

    # 3. Direct client connection host
    if request.client and request.client.host:
        valid_client = _validate_ip_address(request.client.host)
        if valid_client:
            return valid_client

    return "127.0.0.1"


def get_ip_hash_salt() -> str:
    """Returns a stable, cross-instance salt for IP hashing."""
    if settings.IP_HASH_SALT and settings.IP_HASH_SALT.strip():
        return settings.IP_HASH_SALT.strip()
    secret = settings.guest_session_secret
    if secret:
        import hmac
        return hmac.new(secret.encode("utf-8"), b"agentpay-nexus-ip-salt-v1", hashlib.sha256).hexdigest()
    return "agentpay-ip-hash-salt-dev"


def hash_client_ip(ip: str) -> str:
    """Hashes client IP with a stable salt so raw IPs are never stored in the database."""
    salt = get_ip_hash_salt()
    digest = hashlib.sha256(f"{ip}:{salt}".encode("utf-8")).hexdigest()
    return digest[:32]


def check_and_increment_counter(
    db: Session,
    key: str,
    max_count: int,
    window_seconds: int = 3600,
    current_time: Optional[datetime] = None
) -> Tuple[bool, int, int]:
    """Atomic fixed-window rate limiter using persistent database-level UPSERT.
    Executes a single atomic INSERT ... ON CONFLICT DO UPDATE RETURNING statement
    in both PostgreSQL and SQLite, preventing lost updates and race conditions.
    When the window has expired (rate_limits.expires_at <= :now), the counter atomically
    resets to 1 and refreshes window_start and expires_at to start a new window.

    Returns:
        (is_allowed: bool, current_count: int, retry_after_seconds: int)
    """
    now = current_time if current_time is not None else get_current_time()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if max_count <= 0:
        record = db.query(RateLimitRecord).filter(RateLimitRecord.key == key).first()
        if record and record.expires_at:
            rec_exp = record.expires_at
            if rec_exp.tzinfo is None:
                rec_exp = rec_exp.replace(tzinfo=timezone.utc)
            retry_after = max(1, int((rec_exp - now).total_seconds())) if rec_exp > now else window_seconds
        else:
            retry_after = window_seconds
        return False, 0, retry_after

    expires_at = now + timedelta(seconds=window_seconds)

    upsert_query = text("""
        INSERT INTO rate_limits (key, count, window_start, expires_at)
        VALUES (:key, 1, :now, :expires_at)
        ON CONFLICT (key) DO UPDATE SET
            count = CASE
                WHEN rate_limits.expires_at <= :now THEN 1
                ELSE rate_limits.count + 1
            END,
            window_start = CASE
                WHEN rate_limits.expires_at <= :now THEN :now
                ELSE rate_limits.window_start
            END,
            expires_at = CASE
                WHEN rate_limits.expires_at <= :now THEN :expires_at
                ELSE rate_limits.expires_at
            END
        RETURNING count, expires_at;
    """)

    try:
        result = db.execute(upsert_query, {
            "key": key,
            "now": now,
            "expires_at": expires_at
        }).fetchone()
        db.commit()

        if not result:
            raise RateLimiterUnavailableError("UPSERT query did not return a row.")

        current_count = int(result[0])
        raw_exp = result[1]
        if isinstance(raw_exp, str):
            try:
                exp_dt = datetime.fromisoformat(raw_exp)
            except Exception:
                exp_dt = expires_at
        elif isinstance(raw_exp, datetime):
            exp_dt = raw_exp
        else:
            exp_dt = expires_at

        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)

        retry_after = max(1, int((exp_dt - now).total_seconds()))
        is_allowed = (current_count <= max_count)
        return is_allowed, current_count, retry_after

    except SQLAlchemyError as err:
        db.rollback()
        logger.error(f"Distributed rate limit database error for key '{key}': {err}")
        raise RateLimiterUnavailableError(str(err))


def release_active_inflight(db: Session, session_id: str) -> None:
    """Releases an in-flight active task reservation for the session."""
    active_guard_key = f"sess:{session_id}:active_inflight"
    try:
        record = db.query(RateLimitRecord).filter(RateLimitRecord.key == active_guard_key).first()
        if record:
            record.count = max(0, record.count - 1)
            db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to release in-flight reservation for {session_id}: {e}")


def enforce_task_creation_guards(
    request: Request,
    db: Session,
    session_id: str,
    current_time: Optional[datetime] = None
) -> None:
    """Enforces guest session task creation limits, IP rate limits, and concurrent active task caps.
    Fails closed before AI planning begins.
    """
    now = current_time if current_time is not None else get_current_time()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Active task concurrency limit (Max 2 active tasks per guest session)
    try:
        active_count = db.query(TaskModel).filter(
            TaskModel.user_id == session_id,
            TaskModel.status.in_(["planning", "executing", "running"])
        ).count()
    except (SQLAlchemyError, Exception) as err:
        logger.error(f"Cannot verify active task concurrency for session '{session_id}': {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter storage unavailable. Cannot safely initiate task."
        )

    if active_count >= settings.RATE_LIMIT_ACTIVE_TASKS_PER_SESSION:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum concurrent active tasks reached for this session ({settings.RATE_LIMIT_ACTIVE_TASKS_PER_SESSION}). Please complete or wait for existing tasks."
        )

    # 1b. Atomic active creation concurrency guard to prevent simultaneous requests racing
    remaining_active_slots = max(0, settings.RATE_LIMIT_ACTIVE_TASKS_PER_SESSION - active_count)
    active_guard_key = f"sess:{session_id}:active_inflight"
    try:
        active_allowed, _, _ = check_and_increment_counter(
            db=db,
            key=active_guard_key,
            max_count=remaining_active_slots,
            window_seconds=120,  # 2 minute safety TTL
            current_time=now
        )
    except (RateLimiterUnavailableError, SQLAlchemyError, Exception) as err:
        logger.error(f"Cannot verify active task concurrency guard: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter storage unavailable. Cannot safely initiate task."
        )

    if not active_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum concurrent active tasks reached for this session ({settings.RATE_LIMIT_ACTIVE_TASKS_PER_SESSION}). Please complete or wait for existing tasks."
        )

    # 2. Guest Session hourly limit (Max 2 tasks per hour per session)
    session_key = f"sess:{session_id}:task_create"
    try:
        sess_allowed, _, retry_after = check_and_increment_counter(
            db=db,
            key=session_key,
            max_count=settings.RATE_LIMIT_GUEST_TASKS_PER_HOUR,
            window_seconds=3600,
            current_time=now
        )
    except (RateLimiterUnavailableError, SQLAlchemyError, Exception) as err:
        logger.error(f"Cannot verify session rate limit: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter storage unavailable. Cannot safely initiate task."
        )

    if not sess_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Hourly task creation limit reached for this session (limit: {settings.RATE_LIMIT_GUEST_TASKS_PER_HOUR}/hour). Please try again later.",
            headers={"Retry-After": str(retry_after)}
        )

    # 3. IP hourly limit (Max 10 tasks per hour per IP)
    raw_ip = extract_client_ip(request)
    hashed_ip = hash_client_ip(raw_ip)
    ip_key = f"ip:{hashed_ip}:task_create"
    try:
        ip_allowed, _, retry_after_ip = check_and_increment_counter(
            db=db,
            key=ip_key,
            max_count=settings.RATE_LIMIT_IP_TASKS_PER_HOUR,
            window_seconds=3600,
            current_time=now
        )
    except (RateLimiterUnavailableError, SQLAlchemyError, Exception) as err:
        logger.error(f"Cannot verify IP rate limit: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter storage unavailable. Cannot safely initiate task."
        )

    if not ip_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Hourly task creation limit reached for your IP address (limit: {settings.RATE_LIMIT_IP_TASKS_PER_HOUR}/hour). Please try again later.",
            headers={"Retry-After": str(retry_after_ip)}
        )


def enforce_step_advancement_guards(
    request: Request,
    db: Session,
    session_id: str,
    current_time: Optional[datetime] = None
) -> None:
    """Enforces guest session and IP-level rate limits on AI step advancement execution.
    Fails closed before any agent step execution or Gemini inference begins.
    """
    now = current_time if current_time is not None else get_current_time()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Guest Session step execution hourly limit
    session_key = f"sess:{session_id}:step_advance"
    try:
        sess_allowed, _, retry_after = check_and_increment_counter(
            db=db,
            key=session_key,
            max_count=settings.RATE_LIMIT_GUEST_STEPS_PER_HOUR,
            window_seconds=3600,
            current_time=now
        )
    except (RateLimiterUnavailableError, SQLAlchemyError, Exception) as err:
        logger.error(f"Cannot verify session step rate limit: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter storage unavailable. Cannot safely advance task."
        )

    if not sess_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Hourly workflow execution limit reached for this session (limit: {settings.RATE_LIMIT_GUEST_STEPS_PER_HOUR} steps/hour). Please try again later.",
            headers={"Retry-After": str(retry_after)}
        )

    # 2. IP-level step execution hourly limit
    raw_ip = extract_client_ip(request)
    hashed_ip = hash_client_ip(raw_ip)
    ip_key = f"ip:{hashed_ip}:step_advance"
    try:
        ip_allowed, _, retry_after_ip = check_and_increment_counter(
            db=db,
            key=ip_key,
            max_count=settings.RATE_LIMIT_IP_STEPS_PER_HOUR,
            window_seconds=3600,
            current_time=now
        )
    except (RateLimiterUnavailableError, SQLAlchemyError, Exception) as err:
        logger.error(f"Cannot verify IP step rate limit: {err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter storage unavailable. Cannot safely advance task."
        )

    if not ip_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Hourly workflow execution limit reached for your IP address (limit: {settings.RATE_LIMIT_IP_STEPS_PER_HOUR} steps/hour). Please try again later.",
            headers={"Retry-After": str(retry_after_ip)}
        )
