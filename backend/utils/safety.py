"""
Production safety checks and validation.
"""

from typing import Optional
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


def validate_production_safety() -> None:
    """
    Validate production safety requirements.
    Raises RuntimeError if safety checks fail.
    """
    settings = get_settings()
    errors = []
    
    # Check required Supabase config
    if not settings.SUPABASE_URL:
        errors.append("SUPABASE_URL must be set")
    if not settings.SUPABASE_ANON_KEY:
        errors.append("SUPABASE_ANON_KEY must be set")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        errors.append("SUPABASE_SERVICE_ROLE_KEY must be set")
    if not settings.SUPABASE_JWT_SECRET:
        errors.append("SUPABASE_JWT_SECRET must be set")
    if not settings.DATABASE_URL and not settings.SUPABASE_DB_PASSWORD:
        errors.append("Either DATABASE_URL or SUPABASE_DB_PASSWORD must be set")
    
    # Check embedding provider
    if settings.USE_COHERE and not settings.COHERE_API_KEY:
        errors.append("COHERE_API_KEY must be set when USE_COHERE=true")
    elif not settings.USE_COHERE and not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY must be set when USE_COHERE=false")
    
    # Check LLM provider (OpenAI is required, others are optional)
    if not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY must be set (OpenAI is required, Gemini and Groq are optional fallbacks)")
    
    # Check production environment
    if settings.ENV.lower() == "production":
        # Additional production checks
        if settings.ALLOWED_ORIGINS == "http://localhost:3000":
            logger.warning("Production environment detected but ALLOWED_ORIGINS is set to localhost")
        
        # Check for placeholder values
        if "your-" in settings.SUPABASE_URL.lower() or "example" in settings.SUPABASE_URL.lower():
            errors.append("SUPABASE_URL appears to contain placeholder value")
        if "your-" in settings.SUPABASE_ANON_KEY.lower() or len(settings.SUPABASE_ANON_KEY) < 20:
            errors.append("SUPABASE_ANON_KEY appears invalid")
    
    if errors:
        error_msg = "Production safety validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info("Production safety validation passed")


def enforce_user_isolation(user_id: str, query_user_id: Optional[str] = None) -> None:
    """
    Enforce user isolation - ensure user_id matches query.
    
    Args:
        user_id: Authenticated user ID
        query_user_id: User ID from query/request
        
    Raises:
        ValueError: If user IDs don't match
    """
    if query_user_id and user_id != query_user_id:
        logger.error(f"User isolation violation: authenticated={user_id[:8]}..., query={query_user_id[:8]}...")
        raise ValueError("User isolation violation: user_id mismatch")


def validate_no_training_data_access() -> None:
    """
    Validate that no training data access is configured.
    This is a placeholder for future checks.
    """
    # Future: Check for any training data access patterns
    pass

