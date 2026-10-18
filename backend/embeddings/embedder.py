"""
Embedding generation service with Cohere default and OpenAI fallback.
"""

from typing import List, Optional
import numpy as np
from openai import AsyncOpenAI
import cohere
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


class Embedder:
    """
    Unified embedding service with Cohere default and OpenAI fallback.
    Validates dimension consistency with pgvector schema.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.use_cohere = self.settings.USE_COHERE
        
        # Try Cohere first (default)
        if self.use_cohere:
            if not self.settings.COHERE_API_KEY:
                logger.warning("USE_COHERE=true but COHERE_API_KEY not set, falling back to OpenAI")
                self.use_cohere = False
        
        # Fallback to OpenAI if Cohere not available
        if not self.use_cohere:
            if not self.settings.OPENAI_API_KEY:
                raise ValueError(
                    "No embedding provider available. Set either COHERE_API_KEY "
                    "(with USE_COHERE=true) or OPENAI_API_KEY"
                )
        
        # Initialize provider
        if self.use_cohere:
            self.cohere_client = cohere.AsyncClient(self.settings.COHERE_API_KEY)
            self.model = "embed-english-v3.0"
            self.embedding_dimension = 1024  # Cohere embed-v3 fixed dimension
            self.provider = "cohere"
            logger.info("Initialized embedding provider: Cohere embed-v3 (1024 dim)")
        else:
            self.openai_client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
            self.model = self.settings.EMBEDDING_MODEL
            self.embedding_dimension = self.settings.EMBEDDING_DIMENSION
            self.provider = "openai"
            # Validate OpenAI dimension
            if self.embedding_dimension > 3072:
                raise ValueError("OpenAI embeddings support max dimension 3072")
            logger.info(f"Initialized embedding provider: OpenAI {self.model} ({self.embedding_dimension} dim)")
        
        # Validate dimension matches pgvector schema (max 3072)
        if self.embedding_dimension > 3072:
            raise ValueError(
                f"Embedding dimension {self.embedding_dimension} exceeds pgvector schema limit (3072). "
                "Update database schema or reduce dimension."
            )
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Embedding vector
        """
        if self.use_cohere:
            response = await self.cohere_client.embed(
                texts=[text],
                model=self.model,
                input_type="search_document"
            )
            return response.embeddings[0]
        else:
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.embedding_dimension
            )
            return response.data[0].embedding
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        if not texts:
            return []
        
        if self.use_cohere:
            response = await self.cohere_client.embed(
                texts=texts,
                model=self.model,
                input_type="search_document"
            )
            return response.embeddings
        else:
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.embedding_dimension
            )
            return [item.embedding for item in response.data]
    
    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this embedder."""
        return self.embedding_dimension
    
    def get_provider(self) -> str:
        """Get the current embedding provider name."""
        return self.provider


# Global embedder instance
_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """Get or create embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder

