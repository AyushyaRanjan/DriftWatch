"""Gemma calls through the Gemini API."""

from __future__ import annotations

import mimetypes
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

_DEFAULT_MODEL = "gemma-4-26b-a4b-it"
_MAX_ATTEMPTS = 3
_IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


class LLMError(RuntimeError):
    """A Gemma call could not be completed."""


class LLMClient(Protocol):
    def generate(self, prompt: str, image_path: str | None = None) -> str:
        """Return the visible text of one model reply."""


class GemmaClient:
    """One Gemma call per generate(), with temperature 0."""

    def __init__(
        self,
        client: Any | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise LLMError(
                "GEMINI_API_KEY is not set. Add it to the environment or a local .env file."
            )
        configured = os.environ.get("GEMMA_MODEL", "").strip()
        self._model = configured or _DEFAULT_MODEL
        self._sleep = sleep or time.sleep
        self._client = client if client is not None else genai.Client(api_key=api_key)

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, image_path: str | None = None) -> str:
        contents: str | list[Any]
        if image_path is None:
            contents = prompt
        else:
            contents = [_inline_image(image_path), prompt]
        config = types.GenerateContentConfig(temperature=0)
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
            except LLMError:
                raise
            except Exception as exc:
                if _is_retryable(exc) and attempt < _MAX_ATTEMPTS:
                    self._sleep(float(2 ** (attempt - 1)))
                    continue
                if _is_retryable(exc):
                    raise LLMError(
                        f"Gemma request failed after {_MAX_ATTEMPTS} attempts."
                    ) from exc
                raise LLMError("Gemma request failed.") from exc
            return _visible_text(response)
        raise LLMError(f"Gemma request failed after {_MAX_ATTEMPTS} attempts.")


def _is_retryable(exc: BaseException) -> bool:
    if not isinstance(exc, errors.APIError):
        return False
    if isinstance(exc, errors.ServerError):
        return True
    code = exc.code
    if code == 429:
        return True
    if isinstance(code, int) and 500 <= code <= 599:
        return True
    status = exc.status or ""
    return status.upper() in {"RESOURCE_EXHAUSTED", "UNAVAILABLE", "RATE_LIMIT_EXCEEDED"}


def _visible_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text != "":
        return text
    raise LLMError("Gemma reply contained no visible text.")


def _inline_image(image_path: str) -> types.Part:
    path = Path(image_path)
    if not path.is_file():
        raise LLMError(f"Image file not found: {image_path}")
    mime_type = _mime_type(path)
    return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type)


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _IMAGE_MIME_TYPES:
        return _IMAGE_MIME_TYPES[suffix]
    guessed, _encoding = mimetypes.guess_type(path.name)
    if guessed and guessed.startswith("image/"):
        return guessed
    raise LLMError(
        f"Unsupported image type '{suffix or path.name}'. Use a PNG, JPEG, WEBP, or GIF."
    )
