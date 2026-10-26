"""Live check that Gemma 4 answers through the Gemini API.

Reads GEMINI_API_KEY and GEMMA_MODEL from the environment or a local .env file.
Does not print the key.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from driftwatch.llm import GemmaClient


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY is not set. Add it to the environment or a local .env file.")
        return 1
    if api_key == "your-key-here":
        print("GEMINI_API_KEY is still the placeholder from .env.example.")
        return 1

    model = os.environ.get("GEMMA_MODEL", "").strip() or "gemma-4-26b-a4b-it"
    print(f"GEMMA_MODEL={model}")
    client = genai.Client(api_key=api_key)

    try:
        names = _gemma_model_names(client)
    except errors.APIError as exc:
        _print_failure("list models", exc)
        return 1

    print("Gemma models:")
    if not names:
        print("(none)")
    for name in names:
        print(name)

    if not _model_is_listed(model, names):
        print(f"STOP: configured GEMMA_MODEL {model!r} is not in the Gemma model list.")
        print("Which model should DriftWatch use?")
        return 2

    print("configured model is listed: yes")
    prompt = 'Return only a JSON object with one key "ok" set to true.'
    try:
        reply = GemmaClient(client=client).generate(prompt)
    except Exception as exc:
        _print_failure("JSON prompt", exc)
    else:
        print("RAW REPLY:")
        print(reply)
        print(f"PARSED_AS_JSON: {'yes' if _parses_as_json(reply) else 'no'}")

    _probe(
        "temperature 0",
        lambda: client.models.generate_content(
            model=model,
            contents="Reply with the word ok.",
            config=types.GenerateContentConfig(temperature=0),
        ),
    )
    _probe(
        "response_mime_type application/json",
        lambda: client.models.generate_content(
            model=model,
            contents='Return a JSON object with one key "ok" set to true.',
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        ),
    )
    _probe(
        "system instruction",
        lambda: client.models.generate_content(
            model=model,
            contents="Reply with the word ok.",
            config=types.GenerateContentConfig(
                system_instruction="Reply with exactly the word ok."
            ),
        ),
    )
    return 0


def _gemma_model_names(client: genai.Client) -> list[str]:
    names: list[str] = []
    for model in client.models.list():
        name = getattr(model, "name", None)
        if isinstance(name, str) and "gemma" in name.lower():
            names.append(name)
    return names


def _model_is_listed(configured: str, names: list[str]) -> bool:
    wanted = _ids(configured)
    for name in names:
        if wanted & _ids(name):
            return True
    return False


def _ids(name: str) -> set[str]:
    bare = name.strip()
    prefix = "models/"
    if bare.startswith(prefix):
        bare = bare[len(prefix) :]
    return {bare, prefix + bare}


def _parses_as_json(reply: str) -> bool:
    try:
        json.loads(reply.strip())
    except json.JSONDecodeError:
        return False
    return True


def _probe(label: str, call: Any) -> None:
    try:
        call()
    except Exception as exc:
        _print_failure(label, exc)
        return
    print(f"{label}: PASS")


def _print_failure(label: str, exc: BaseException) -> None:
    detail = type(exc).__name__
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    if code is not None:
        detail += f" code={code}"
    if status:
        detail += f" status={status}"
    line = f"{label}: FAIL ({detail})"
    secret = os.environ.get("GEMINI_API_KEY", "").strip()
    if secret and secret in line:
        line = line.replace(secret, "[redacted]")
    print(line)


if __name__ == "__main__":
    raise SystemExit(main())
