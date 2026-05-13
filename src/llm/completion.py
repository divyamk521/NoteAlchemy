
from __future__ import annotations

import json
import time
from typing import Any

from groq import Groq

from config.settings import get_settings
from src.utils.logger import get_logger
from src.utils.retry import groq_retry

logger = get_logger(__name__)
settings = get_settings()

class CompletionError(RuntimeError):
    """Raised when a completion call fails after all retries."""

def _strip_json_fences(raw: str) -> str:
    """Remove markdown code fences that models sometimes wrap JSON in."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove first line (``` or ```json) and last ```
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
        stripped = "\n".join(lines).strip()
    return stripped

class LLMClient:
   
    def __init__(self, client: Groq) -> None:
        self._client = client

   
    @groq_retry
    def complete(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.4,
        max_tokens: int = 1500,
    ) -> str:
        """
        Send a chat-completion request and return the assistant's text.

        Returns
        -------
        str : raw assistant response text

        Raises
        ------
        CompletionError : on persistent failure after retries
        """
        t0 = time.perf_counter()#timer starts
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise CompletionError(
                f"Groq completion failed (model={model}): {exc}"
            ) from exc

        elapsed = time.perf_counter() - t0#timer ends
        text = response.choices[0].message.content or ""#response
        tokens = getattr(response.usage, "total_tokens", "?")#token usage
        logger.debug(
            f"complete() model={model} tokens={tokens} "
            f"elapsed={elapsed:.2f}s"
        )
        return text.strip()

  #for some sections like glossary we need json output format

    def complete_json(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> Any:
        """
        Like :meth:`complete` but parse and return the response as JSON.

        Raises
        ------
        CompletionError : if the response is not valid JSON after stripping fences
        """
        raw = self.complete(
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        clean = _strip_json_fences(raw)#it cleans markdown and converts that to structured json
        try:
            return json.loads(clean)
        except json.JSONDecodeError as exc:
            raise CompletionError(
                f"Model did not return valid JSON.\nRaw response:\n{raw[:500]}"
            ) from exc
