import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import Session

from api.config import settings
from api.models.task import TaskModel

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Base exception for session authentication errors."""
    pass


class TamperedTokenError(SessionError):
    """Raised when HMAC signature verification fails."""
    pass


class ExpiredTokenError(SessionError):
    """Raised when token lifetime has elapsed."""
    pass


class SecretConfigError(SessionError):
    """Raised when session signing secret is unconfigured in production/hosted environment."""
    pass


def get_session_signing_secret() -> str:
    """Retrieves session signing secret.
    Fails closed if running in hosted/production environments without an explicit secret.
    """
    secret = settings.guest_session_secret
    if not secret:
        raise SecretConfigError("GUEST_SESSION_SECRET is not configured for hosted/production environment.")
    return secret


def generate_guest_id() -> str:
    """Generates a cryptographically random guest user ID."""
    return f"guest:{uuid.uuid4()}"


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def base64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


def create_guest_session_token(
    uid: Optional[str] = None,
    expires_in_seconds: Optional[int] = None,
    custom_secret: Optional[str] = None
) -> str:
    """Creates a cryptographically signed guest session token.
    Format: base64url(payload).base64url(hmac_signature)
    """
    secret = custom_secret or get_session_signing_secret()
    guest_uid = uid or generate_guest_id()
    now = int(time.time())
    exp = now + (expires_in_seconds if expires_in_seconds is not None else settings.GUEST_SESSION_EXPIRY_DAYS * 86400)

    payload = {
        "v": 1,
        "uid": guest_uid,
        "iat": now,
        "exp": exp
    }
    payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    b64_payload = base64url_encode(payload_json)

    signature = hmac.new(
        secret.encode("utf-8"),
        b64_payload.encode("ascii"),
        hashlib.sha256
    ).digest()
    b64_sig = base64url_encode(signature)

    return f"{b64_payload}.{b64_sig}"


def verify_guest_session_token(token: str, custom_secret: Optional[str] = None) -> Dict[str, Any]:
    """Validates signature, structure, and expiration of a guest session token."""
    if not token or "." not in token:
        raise TamperedTokenError("Malformed session token format.")

    parts = token.split(".")
    if len(parts) != 2:
        raise TamperedTokenError("Invalid token segments.")

    b64_payload, b64_sig = parts[0], parts[1]

    secret = custom_secret or get_session_signing_secret()
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        b64_payload.encode("ascii"),
        hashlib.sha256
    ).digest()

    try:
        received_sig = base64url_decode(b64_sig)
    except Exception:
        raise TamperedTokenError("Corrupt signature encoding.")

    if not hmac.compare_digest(expected_sig, received_sig):
        raise TamperedTokenError("Session signature verification failed.")

    try:
        payload_bytes = base64url_decode(b64_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise TamperedTokenError("Corrupt payload decoding.")

    if not isinstance(payload, dict):
        raise TamperedTokenError("Payload must be a JSON object.")

    exp = payload.get("exp")
    if not exp or not isinstance(exp, (int, float)):
        raise TamperedTokenError("Missing or invalid expiration in token.")

    if time.time() > exp:
        raise ExpiredTokenError(f"Session token expired at {exp}.")

    uid = payload.get("uid")
    if not uid or not isinstance(uid, str):
        raise TamperedTokenError("Missing or invalid user identity in token.")

    return payload


def set_guest_session_cookie(response: Response, token: str) -> None:
    """Sets a host-only, HTTP-only, secure guest session cookie on the response."""
    # Strict security flags: host-only (no domain), HttpOnly, SameSite Lax
    is_secure = bool(settings.is_hosted or settings.is_production)
    max_age = settings.GUEST_SESSION_EXPIRY_DAYS * 86400
    response.set_cookie(
        key=settings.GUEST_SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/"
    )


def get_or_create_client_session_id(client) -> str:
    """Test fixture helper: extracts or injects a signed guest session on a TestClient."""
    cookie_token = client.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    if cookie_token:
        try:
            payload = verify_guest_session_token(cookie_token)
            return payload["uid"]
        except Exception:
            pass
    uid = generate_guest_id()
    token = create_guest_session_token(uid=uid)
    client.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, token)
    return uid


async def get_current_session(request: Request, response: Response) -> str:
    """FastAPI dependency: Resolves, verifies, or issues a secure guest session identity.

    Rules:
    - Never uses fixed 'user_guest_01'.
    - Arbitrary Bearer headers cannot forge an identity (rejected with 401).
    - Tampered or corrupt session cookies are rejected with 401.
    - Expired session cookies are rejected with 401.
    - Missing session cookies trigger automatic issuance of a new random guest identity.
    - Hosted environments lacking GUEST_SESSION_SECRET fail closed with 503.
    """
    # 1. Arbitrary Bearer header lockout: prevent forged identities
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.strip():
        # Reject unvalidated Bearer tokens categorically (Phase 2A does not implement Supabase JWT validation)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token authentication is unverified. Use secure guest session cookies."
        )

    # 2. Extract cookie
    cookie_token = request.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)

    if cookie_token:
        try:
            payload = verify_guest_session_token(cookie_token)
            return payload["uid"]
        except SecretConfigError as sce:
            logger.error(f"Guest session secret misconfigured: {sce}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Guest session service configuration unavailable."
            )
        except TamperedTokenError as tte:
            logger.warning(f"Tampered guest session rejected: {tte}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session signature."
            )
        except ExpiredTokenError as ete:
            logger.info(f"Expired guest session rejected: {ete}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired."
            )

    # 3. No cookie present: generate new unique guest identity
    try:
        new_uid = generate_guest_id()
        new_token = create_guest_session_token(uid=new_uid)
        set_guest_session_cookie(response, new_token)
        return new_uid
    except SecretConfigError as sce:
        logger.error(f"Cannot initialize guest session: {sce}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Guest session service configuration unavailable."
        )


def verify_task_ownership(task_id: str, session_id: str, db: Session) -> TaskModel:
    """Verifies that the requested task exists and belongs strictly to the verified session.
    Fails closed with 404 Not Found so unauthorized visitors cannot deduce task existence.
    """
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task or task.user_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
    return task
