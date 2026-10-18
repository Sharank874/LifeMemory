"""
Centralized configuration using pydantic-settings.
Single source of truth for all environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment
    ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    DATABASE_URL: Optional[str] = None
    SUPABASE_DB_PASSWORD: Optional[str] = None
    
    # Embedding Configuration
    USE_COHERE: bool = True  # Default to Cohere
    COHERE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "embed-english-v3.0"  # Cohere default
    EMBEDDING_DIMENSION: int = 1024  # Cohere dimension
    
    # LLM Configuration (with fallback support)
    # Default model names (used as fallback if not specified)
    # Note: Actual models are hardcoded in llm/router.py for safety
    LLM_MODEL: str = "gpt-4o-mini"  # Default OpenAI model (final fallback)
    LLM_TEMPERATURE: float = 0.3
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: Optional[str] = None
    
    # LangGraph Configuration
    MAX_RETRIEVED_MEMORIES: int = 15
    MAX_CONTEXT_TOKENS: int = 4000
    MIN_EVIDENCE_THRESHOLD: int = 1
    MIN_RELEVANCE_SCORE: float = 0.3
    
    # MLOps Configuration
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "life-memory-ai"
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "life-memory-ai"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENV.lower() == "development"
    
    def validate_embedding_config(self) -> None:
        """Validate embedding configuration."""
        if self.USE_COHERE:
            if not self.COHERE_API_KEY:
                raise ValueError("COHERE_API_KEY must be set when USE_COHERE=true")
            # Cohere embed-v3 always uses 1024 dimensions - override if set incorrectly
            if self.EMBEDDING_DIMENSION != 1024:
                import warnings
                warnings.warn(
                    f"Cohere embed-v3 requires dimension 1024, but {self.EMBEDDING_DIMENSION} was set. "
                    "Automatically setting to 1024."
                )
                self.EMBEDDING_DIMENSION = 1024
        else:
            if not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY must be set when USE_COHERE=false")
            if self.EMBEDDING_DIMENSION > 3072:
                raise ValueError("OpenAI embeddings support max dimension 3072")
    
    def validate_supabase_config(self) -> None:
        """Validate Supabase configuration."""
        if not self.SUPABASE_URL:
            raise ValueError("SUPABASE_URL must be set")
        if not self.SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_ANON_KEY must be set")
        if not self.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY must be set")
        if not self.SUPABASE_JWT_SECRET:
            raise ValueError("SUPABASE_JWT_SECRET must be set")
        if not self.DATABASE_URL and not self.SUPABASE_DB_PASSWORD:
            raise ValueError("Either DATABASE_URL or SUPABASE_DB_PASSWORD must be set")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use lru_cache to ensure single instance.
    """
    settings = Settings()
    settings.validate_supabase_config()
    settings.validate_embedding_config()
    return settings

