"""
LLM router with ordered fallback: OpenAI -> Gemini -> Groq.
"""

from typing import Any, Optional
from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from config.settings import get_settings
import logging
import httpx

logger = logging.getLogger("llm.router")
FALLBACK_MESSAGE = "I don't have enough evidence from your entries to answer this confidently."


class LLMRouter:
    """Provider-agnostic router with strict fallback order."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._last_provider: str = "fallback"
        self._gemini_available: Optional[bool] = None

    def _check_gemini_model_available(self, api_key: str, model: str) -> bool:
        """Fast preflight check to avoid long internal Gemini retries on 404 models."""
        if self._gemini_available is not None:
            return self._gemini_available
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, params={"key": api_key})
            self._gemini_available = resp.status_code == 200
        except Exception:
            self._gemini_available = False
        return self._gemini_available

    def _get_openai(self) -> ChatOpenAI:
        if self.settings.OPENAI_API_KEY is None or not self.settings.OPENAI_API_KEY.strip():
            raise ValueError("OPENAI_API_KEY not configured")
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=self.settings.OPENAI_API_KEY,
            temperature=0.3,
            max_retries=0,
        )

    def _get_gemini(self) -> ChatGoogleGenerativeAI:
        if self.settings.GEMINI_API_KEY is None or not self.settings.GEMINI_API_KEY.strip():
            raise ValueError("GEMINI_API_KEY not configured")
        model_name = "gemini-2.0-flash"
        # if not self._check_gemini_model_available(self.settings.GEMINI_API_KEY, model_name):
        #    raise ValueError(f"GEMINI model not available: {model_name}")
        return ChatGoogleGenerativeAI(
            # Use a broadly available model alias to avoid 404 on versioned IDs.
            model=model_name,
            google_api_key=self.settings.GEMINI_API_KEY,
            temperature=0.3,
            convert_system_message_to_human=True,
        )

    def _get_groq(self) -> ChatGroq:
        if self.settings.GROQ_API_KEY is None or not self.settings.GROQ_API_KEY.strip():
            raise ValueError("GROQ_API_KEY not configured")
        # Support both newer (api_key) and older (groq_api_key) langchain-groq signatures.
        try:
            return ChatGroq(
                model="llama-3.1-8b-instant",
                api_key=self.settings.GROQ_API_KEY,
                temperature=0.3,
            )
        except TypeError:
            return ChatGroq(
                model="llama-3.1-8b-instant",
                groq_api_key=self.settings.GROQ_API_KEY,
                temperature=0.3,
            )

    def invoke(self, messages: list[BaseMessage]) -> Any:
        providers = [
            ("Groq", self._get_groq),
            ("Gemini", self._get_gemini),
        ]
        for name, factory in providers:
            logger.info(f"Attempting {name}...")
            try:
                llm = factory()
                result = llm.invoke(messages)
                self._last_provider = name.lower()
                logger.info(f"{name} succeeded")
                return result
            except ValueError as e:
                logger.warning(f"{name} skipped — not configured: {e}")
                continue
            except Exception as e:
                logger.warning(f"{name} call failed: {e}")
                continue
        logger.error("All LLM providers failed. Returning safe fallback message.")
        self._last_provider = "fallback"
        return AIMessage(content=FALLBACK_MESSAGE)

    def invoke_with_provider_name(self, messages: list[BaseMessage]) -> tuple[Any, str]:
        providers = [
            ("Groq", self._get_groq),
            ("Gemini", self._get_gemini),
        ]
        for name, factory in providers:
            logger.info(f"Attempting {name}...")
            try:
                llm = factory()
                result = llm.invoke(messages)
                self._last_provider = name.lower()
                logger.info(f"{name} succeeded")
                return result, name.lower()
            except ValueError as e:
                logger.warning(f"{name} skipped — not configured: {e}")
                continue
            except Exception as e:
                logger.warning(f"{name} call failed: {e}")
                continue
        logger.error("All LLM providers failed. Returning safe fallback message.")
        self._last_provider = "fallback"
        return AIMessage(content=FALLBACK_MESSAGE), "fallback"

    def get_provider(self) -> str:
        return self._last_provider


llm_router = LLMRouter()


def get_router() -> LLMRouter:
    """Backward-compatible router getter."""
    return llm_router


def get_llm_provider() -> str:
    """Get the last used provider name for logging."""
    return llm_router.get_provider()


async def generate_with_fallback(messages: list[BaseMessage]) -> str:
    """Main async entry point used by graph nodes."""
    result, provider = llm_router.invoke_with_provider_name(messages)
    llm_router._last_provider = provider
    if isinstance(result, AIMessage):
        return result.content
    if hasattr(result, "content"):
        return result.content
    return str(result)


def get_llm() -> Any:
    """Backward-compatibility shim for legacy references."""
    return llm_router._get_openai()
