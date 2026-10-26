"""Offline tests for the Gemma client. These tests must not use the network."""

import pytest
from google.genai import errors, types

from driftwatch.llm import GemmaClient, LLMError

SENTINEL = "dw-test-key-do-not-print-9f3a"


def _silence_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("driftwatch.llm.load_dotenv", lambda *_args, **_kwargs: False)


def _rate_limit() -> errors.ClientError:
    return errors.ClientError(
        429,
        {"message": "resource exhausted", "status": "RESOURCE_EXHAUSTED"},
    )


def _unavailable() -> errors.ServerError:
    return errors.ServerError(
        503,
        {"message": "unavailable", "status": "UNAVAILABLE"},
    )


class _Models:
    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _Sdk:
    def __init__(self, outcomes: list[object]) -> None:
        self.models = _Models(outcomes)


class _Reply:
    def __init__(self, text: str) -> None:
        self.text = text


def test_missing_key_names_variable_and_hides_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_dotenv(monkeypatch)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OTHER_SECRET", SENTINEL)

    with pytest.raises(LLMError) as caught:
        GemmaClient()

    message = str(caught.value)
    assert "GEMINI_API_KEY" in message
    assert SENTINEL not in message


def test_transient_error_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_dotenv(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    monkeypatch.delenv("GEMMA_MODEL", raising=False)
    sleeps: list[float] = []
    sdk = _Sdk([_rate_limit(), _Reply('{"ok": true}')])

    client = GemmaClient(client=sdk, sleep=sleeps.append)
    reply = client.generate("Return JSON.")

    assert reply == '{"ok": true}'
    assert len(sdk.models.calls) == 2
    assert sleeps == [1.0]
    assert sdk.models.calls[0]["model"] == "gemma-4-26b-a4b-it"
    config = sdk.models.calls[0]["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.temperature == 0
    assert SENTINEL not in reply


def test_raises_clear_error_after_three_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    _silence_dotenv(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    sdk = _Sdk([_unavailable(), _unavailable(), _rate_limit()])

    client = GemmaClient(client=sdk, sleep=lambda _seconds: None)
    with pytest.raises(LLMError) as caught:
        client.generate("Return JSON.")

    assert len(sdk.models.calls) == 3
    message = str(caught.value)
    assert "3" in message
    assert "attempt" in message
    assert SENTINEL not in message
