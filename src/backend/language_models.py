"""Google Gemini client wrapper.

Gemini is the only AI provider in this system. It provides exactly two
capabilities used by the app: text generation (the consultant's answers) and
text embeddings (the property vector index).
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from config import (
    EMBEDDING_BATCH_SIZE,
    GEMINI_CHAT_MODEL,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_TEMPERATURE,
    GOOGLE_API_KEY,
)

logger = logging.getLogger(__name__)


class GeminiUnavailableError(RuntimeError):
    """Raised when Gemini is not configured or an API call fails."""


class GeminiClient:
    """Thin wrapper around the official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GOOGLE_API_KEY
        self.chat_model_name = GEMINI_CHAT_MODEL
        self.embedding_model_name = GEMINI_EMBEDDING_MODEL
        self._lock = threading.Lock()
        self._client: Optional[genai.Client] = None

        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)
            logger.info(
                "Gemini configured (chat=%s, embedding=%s)",
                self.chat_model_name,
                self.embedding_model_name,
            )
        else:
            logger.error("GOOGLE_API_KEY is not set - AI features will not work.")

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def _require_client(self) -> genai.Client:
        if self._client is None:
            raise GeminiUnavailableError(
                "GOOGLE_API_KEY is not configured. Set it in src/backend/.env"
            )
        return self._client

    # --- Text generation ----------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_instruction: str,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """Generate an answer. `history` is a list of {role, content} dicts."""
        client = self._require_client()

        contents: List[Any] = []
        for turn in history or []:
            text = (turn.get("content") or "").strip()
            if not text:
                continue
            role = "model" if turn.get("role") in ("assistant", "model") else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        try:
            response = client.models.generate_content(
                model=self.chat_model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=(
                        GEMINI_TEMPERATURE if temperature is None else temperature
                    ),
                    max_output_tokens=(
                        GEMINI_MAX_OUTPUT_TOKENS
                        if max_output_tokens is None
                        else max_output_tokens
                    ),
                ),
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller
            logger.exception("Gemini generate_content failed: %s", exc)
            raise GeminiUnavailableError(str(exc)) from exc

        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise GeminiUnavailableError("Gemini returned an empty response")
        return text

    # --- Embeddings ---------------------------------------------------------
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed property documents for indexing."""
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> List[float]:
        """Embed a single search query."""
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]

    def _embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        client = self._require_client()
        vectors: List[List[float]] = []

        with self._lock:
            for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                batch = texts[start : start + EMBEDDING_BATCH_SIZE]
                try:
                    result = client.models.embed_content(
                        model=self.embedding_model_name,
                        contents=batch,
                        config=types.EmbedContentConfig(task_type=task_type),
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Gemini embed_content failed: %s", exc)
                    raise GeminiUnavailableError(str(exc)) from exc

                for embedding in result.embeddings or []:
                    vectors.append(list(embedding.values or []))

        if len(vectors) != len(texts):
            raise GeminiUnavailableError(
                f"Expected {len(texts)} embeddings from Gemini but received {len(vectors)}"
            )
        return vectors


# Shared singleton used across the app.
gemini = GeminiClient()
