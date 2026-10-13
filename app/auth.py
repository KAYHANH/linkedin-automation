"""Authentication and session management module for FounderOS LinkedIn Studio."""

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Dict, Optional, Tuple
import bcrypt
from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)

# Security bearer scheme for optional token header
bearer_scheme = HTTPBearer(auto_error=False)

# In-memory login attempt rate limiting (IP -> (fail_count, first_fail_ts))
_login_attempts: Dict[str, Tuple[int, float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300  # 5 minutes


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionInfo(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    role: Optional[str] = "founder"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against bcrypt hash or direct plain text setting."""
    settings = get_settings()
    if settings.dashboard_password and settings.dashboard_password.strip():
        # Constant-time comparison for plain text DASHBOARD_PASSWORD configured in Render
        return hmac.compare_digest(plain_password, settings.dashboard_password.strip())
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.warning("Password verification failed with error: %s", e)
        return False


# Default dev hash for password "founder123" if no hash configured in env
DEFAULT_DEV_HASH = "$2b$12$TQ.YLTnvKmvsPJUgIl2yeeJWuIdj2.7.v6/UqysBTKLxR2wCp3Ev."


def get_expected_password_hash() -> str:
    """Retrieve password hash from settings or return fallback dev hash."""
    settings = get_settings()
    if settings.dashboard_password_hash and settings.dashboard_password_hash.strip():
        return settings.dashboard_password_hash.strip()
    return DEFAULT_DEV_HASH


def create_session_token(username: str, duration_seconds: int = 86400) -> str:
    """Create an HMAC-SHA256 signed session token."""
    settings = get_settings()
    exp = int(time.time()) + duration_seconds
    payload = json.dumps({"sub": username, "exp": exp}, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8").rstrip("=")
    
    sig = hmac.new(
        settings.session_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{sig}"


def verify_session_token(token: str) -> Optional[str]:
    """Verify an HMAC-SHA256 signed session token. Returns username if valid, None otherwise."""
    if not token or "." not in token:
        return None
    
    settings = get_settings()
    parts = token.split(".", 1)
    if len(parts) != 2:
        return None
    
    payload_b64, sig = parts
    expected_sig = hmac.new(
        settings.session_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(sig, expected_sig):
        return None
    
    # Pad base64 if needed
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(padded)
        data = json.loads(payload_bytes.decode("utf-8"))
        if data.get("exp", 0) < time.time():
            return None  # Expired
        return data.get("sub")
    except Exception:
        return None


def check_rate_limit(client_ip: str) -> None:
    """Check if IP is currently locked out from login attempts."""
    now = time.time()
    if client_ip in _login_attempts:
        count, first_ts = _login_attempts[client_ip]
        if now - first_ts > LOCKOUT_DURATION_SECONDS:
            del _login_attempts[client_ip]
        elif count >= MAX_LOGIN_ATTEMPTS:
            remaining = int(LOCKOUT_DURATION_SECONDS - (now - first_ts))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Locked out for {remaining} seconds."
            )


def record_failed_attempt(client_ip: str) -> None:
    """Increment failed login counter for IP."""
    now = time.time()
    if client_ip in _login_attempts:
        count, first_ts = _login_attempts[client_ip]
        if now - first_ts > LOCKOUT_DURATION_SECONDS:
            _login_attempts[client_ip] = (1, now)
        else:
            _login_attempts[client_ip] = (count + 1, first_ts)
    else:
        _login_attempts[client_ip] = (1, now)


def record_successful_attempt(client_ip: str) -> None:
    """Reset failed attempts on successful login."""
    if client_ip in _login_attempts:
        del _login_attempts[client_ip]


def get_current_user(
    request: Request,
    auth_cookie: Optional[str] = Cookie(None, alias="founderos_session"),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> str:
    """
    FastAPI dependency ensuring request is authenticated via session cookie or bearer token.
    Raises 401 Unauthorized if invalid or missing.
    """
    token = auth_cookie
    if not token and bearer_auth and bearer_auth.credentials:
        token = bearer_auth.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource."
        )
    
    username = verify_session_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again."
        )
    
    return username
