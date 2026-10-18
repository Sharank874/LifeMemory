"""
Supabase authentication and JWT verification middleware.

JWT verification uses OIDC discovery to dynamically fetch JWKS URI.
This is OIDC-compliant and works across all Supabase projects.
OIDC config is loaded lazily on first use so the app can start without
network/DNS (e.g. in Docker) when SUPABASE_URL is not yet reachable.
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jwt import PyJWKClient, decode
from supabase import Client
from database.connection import get_supabase_client
from config.settings import get_settings
import logging
import httpx
import threading

security = HTTPBearer()
logger = logging.getLogger(__name__)

# Lazy-loaded OIDC state (filled on first verify_token call)
_oidc_lock = threading.Lock()
_issuer: Optional[str] = None
_jwks_client: Optional[PyJWKClient] = None


def _ensure_oidc_loaded() -> tuple[str, PyJWKClient]:
    """Load OIDC config and JWKS client on first use; cache and reuse."""
    global _issuer, _jwks_client
    with _oidc_lock:
        if _jwks_client is not None:
            assert _issuer is not None
            return _issuer, _jwks_client
        settings = get_settings()
        url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/openid-configuration"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            oidc_config = resp.json()
        _issuer = oidc_config["issuer"]
        jwks_uri = oidc_config["jwks_uri"]
        _jwks_client = PyJWKClient(jwks_uri)
        logger.info("Loaded OIDC config and initialized JWKS client (lazy)")
        return _issuer, _jwks_client


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify Supabase JWT token using OIDC-discovered JWKS.
    
    This function:
    - Uses JWKS URI discovered via OIDC configuration
    - Verifies token signature using RS256
    - Validates audience and issuer (OIDC-compliant)
    - Extracts user information
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        dict: Token payload containing user_id and other claims
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    try:
        issuer, jwks_client = _ensure_oidc_loaded()
        logger.debug(f"Verifying token: {token[:20]}...")

        # Get signing key from JWKS (discovered via OIDC)
        signing_key = jwks_client.get_signing_key_from_jwt(token).key

        # Decode and verify token with ES256 or RS256
        # Supabase projects may use either algorithm depending on configuration
        # Validate audience and issuer for security (OIDC-compliant)
        payload = decode(
            token,
            signing_key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=issuer,
        )
        
        # Extract user_id from token
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing user_id (sub claim)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        logger.info(f"Token verified successfully for user: {user_id}")
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "token": token
        }
        
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
        )


async def get_current_user(
    token_data: dict = Depends(verify_token)
) -> str:
    """
    Extract user_id from verified token.
    
    Args:
        token_data: Verified token payload from verify_token
        
    Returns:
        str: User ID (UUID)
    """
    return token_data["user_id"]


def get_supabase_rest_headers(token: str) -> dict:
    """
    Get headers for Supabase REST API calls with user authentication.
    
    RLS requires both:
    - Authorization: Bearer <USER_JWT> - establishes auth.uid()
    - apikey: <ANON_KEY> - required for REST API access
    
    Args:
        token: User's JWT token
        
    Returns:
        dict: Headers dict with Authorization and apikey
    """
    settings = get_settings()
    return {
        "Authorization": f"Bearer {token}",
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
