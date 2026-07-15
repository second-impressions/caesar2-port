"""Tests for the GLM-5.2-short -> GLM-5.2 auto-context-fallback.

Short-context models with a known long-context sibling on the same
provider are wrapped in pydantic-ai's :class:`FallbackModel` so a
context-overflow rolls the SAME request over transparently.  See
:func:`c2.decompile.agent._build_model` and
:data:`c2.decompile.agent._AUTO_CONTEXT_FALLBACKS`.
"""

from __future__ import annotations

import os

import pytest

# These tests poke at provider construction which needs the neuralwatt
# key to be set (even a dummy value -- the providers only validate at
# REQUEST time, not at instantiation).  The .env file in the project
# root supplies the real key in normal runs; for CI we backstop with
# a placeholder so the test can still assemble the model objects.
os.environ.setdefault("NEURALWATT_API_KEY", "test-key-not-used-at-import")

from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.fallback import FallbackModel

from c2.decompile.agent import (
    _AUTO_CONTEXT_FALLBACKS,
    _build_model,
    _is_context_overflow,
)


def test_glm_short_wrapped_in_fallback_model():
    """The default short-context model resolves to a FallbackModel
    wrapping the short primary + the long sibling."""
    m = _build_model("neuralwatt:glm-5.2-short")
    assert isinstance(m, FallbackModel)
    assert len(m.models) == 2, "primary + 1 sibling"
    # Both are OpenAIChatModels pointing at the neuralwatt endpoint;
    # we can't easily diff the underlying names without poking private
    # attrs, but the table is the source of truth.
    sibling_id = _AUTO_CONTEXT_FALLBACKS["neuralwatt:glm-5.2-short"]
    assert sibling_id == "neuralwatt:glm-5.2"


def test_glm_short_fast_wrapped_in_fallback_model():
    """The -fast variant has its own sibling pair."""
    m = _build_model("neuralwatt:glm-5.2-short-fast")
    assert isinstance(m, FallbackModel)
    assert len(m.models) == 2


def test_long_models_unwrapped():
    """A long-context model on its own is NOT auto-wrapped (no infinite
    recursion and no extra cost for callers who already picked the
    long sibling)."""
    m = _build_model("neuralwatt:glm-5.2")
    assert not isinstance(m, FallbackModel)


def test_native_pydantic_ai_ids_unwrapped():
    """Native pydantic-ai ids (deepseek:, openai:, anthropic:) pass
    through unchanged -- no fallback table entry, no wrapping."""
    # _build_model returns the string for native ids (pydantic-ai's own
    # ``Agent(model=str)`` then resolves it).
    assert _build_model("deepseek:deepseek-v4-pro") == "deepseek:deepseek-v4-pro"


def test_context_overflow_predicate_hits_common_phrases():
    """The predicate must recognise the various phrasings providers
    use for 'prompt too long for context window'."""
    bodies = [
        {"message": "This model's maximum context length is 200000 tokens. Your request requires 206528 tokens."},
        {"error": {"code": "context_length_exceeded", "message": "..."}},
        {"message": "prompt is too long for the model"},
        "Maximum context length exceeded",  # bare string body
        {"message": "too many tokens in request"},
    ]
    for body in bodies:
        err = ModelHTTPError(status_code=400, model_name="glm-5.2-short", body=body)
        assert _is_context_overflow(err), f"missed: {body!r}"


def test_context_overflow_predicate_ignores_other_400s():
    """A 400 for an unrelated reason (bad tool schema, bad role
    sequence) must NOT silently flip providers."""
    bad_400s = [
        {"message": "invalid tool schema"},
        {"message": "messages.0.role: invalid value"},
        {"message": "unsupported parameter"},
        "Bad Request",
    ]
    for body in bad_400s:
        err = ModelHTTPError(status_code=400, model_name="glm-5.2-short", body=body)
        assert not _is_context_overflow(err), f"false-positive: {body!r}"


def test_context_overflow_predicate_ignores_5xx():
    """5xx errors (provider down / overloaded) are not a context issue
    -- they should bubble, not silently switch model."""
    err = ModelHTTPError(status_code=503, model_name="glm-5.2-short",
                         body={"message": "maximum context length"})
    assert not _is_context_overflow(err)
    err = ModelHTTPError(status_code=500, model_name="glm-5.2-short",
                         body={"message": "internal"})
    assert not _is_context_overflow(err)


def test_context_overflow_predicate_ignores_non_http_errors():
    """Connection errors / timeout / generic Exceptions are not
    fallback triggers."""
    assert not _is_context_overflow(ValueError("oops"))
    assert not _is_context_overflow(TimeoutError("read"))
    assert not _is_context_overflow(Exception("anything"))
