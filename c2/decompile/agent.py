"""Pydantic-AI Agent builder for the decompile subagent.

Wires the tools defined in :mod:`c2.decompile.tools` into a single
``Agent`` with :class:`FinishReport` as its enforced output type — the
agent cannot terminate without emitting a structured verdict.

Model resolution is delegated to pydantic-ai's native provider system:
strings like ``"deepseek:deepseek-v4-pro"``, ``"openai:gpt-5"``,
``"anthropic:claude-opus-4-7"`` are recognised by their respective
``Provider`` classes, each of which reads its OWN well-known env var
(``DEEPSEEK_API_KEY`` / ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` …).

Credentials live in the standard places pydantic-ai already documents:

* a process env var (``DEEPSEEK_API_KEY=sk-…``), OR
* a ``.env`` file in the project root (auto-loaded by this module via
  ``python-dotenv`` on first import) — this is the project-recommended
  spot for the developer's personal key.

Neither is parsed by hand — we just call ``load_dotenv()`` once so the
keys land in ``os.environ`` before any pydantic-ai provider is
constructed.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_ai import Agent

from c2.decompile import tools
from c2.decompile.models import AgentFinishReport, Target
from c2.decompile.prompt import system_prompt
from c2.decompile.tools import AgentDeps


# Load .env once at import-time so every provider lookup (whichever the
# user picked) sees the same credentials.  Silent no-op if the file is
# missing; never overrides an already-set env var (process env wins).
load_dotenv(override=False)


# ── default model ────────────────────────────────────────────────────────
#
# DeepSeek V4 Pro is the project's default; it's a thinking model
# (``deepseek_model_profile`` configures the always-on reasoning channel,
# and pydantic-ai's ``DeepSeekProvider`` knows the base URL + reads
# ``DEEPSEEK_API_KEY`` itself).  Switch with ``--model openai:gpt-5`` or
# any other ``<provider>:<name>`` pydantic-ai understands.

DEFAULT_MODEL_ID = "deepseek:deepseek-v4-pro"

# Registry of OpenAI-compatible third-party endpoints.  Each entry maps
# a model-id PREFIX to ``(base_url, api_key_env_var)``.  Set the env
# var (e.g. in ``.env``) and use ``--model <prefix>:<model-name>``.
# Pydantic-AI's native prefixes (``deepseek:``, ``openai:``, etc.) are
# NOT in this table — they go through pydantic-ai's own resolver.
_OPENAI_COMPAT_ENDPOINTS: dict[str, tuple[str, str]] = {
    "neuralwatt": ("https://api.neuralwatt.com/v1", "NEURALWATT_API_KEY"),
    "requesty":   ("https://router.requesty.ai/v1",  "REQUESTY_API_KEY"),
}

# Registry of Anthropic-compatible endpoints (e.g. the local pi proxy at
# ``http://localhost:8000/anthropic`` that ships with the pi agent
# runtime; see ``~/.pi/agent/models.json``).  Each entry maps a model-id
# PREFIX to ``(base_url, api_key_env_var, env_default)`` — ``env_default``
# is used when the env var is unset, since proxy endpoints typically
# don't require a real key (the proxy injects its own credentials).
_ANTHROPIC_COMPAT_ENDPOINTS: dict[str, tuple[str, str, str]] = {
    # The pi-runtime local Anthropic proxy.  Mirrors the
    # ``anthropic`` provider in ``~/.pi/agent/models.json``.
    "anthropic-proxy":  ("http://localhost:8000/anthropic",  "ANTHROPIC_PROXY_API_KEY",  "not-needed"),
    # Second proxy slot (mirrors ``anthropic-second`` in models.json).
    "anthropic-proxy2": ("http://localhost:8800/anthropic", "ANTHROPIC_PROXY2_API_KEY", "not-needed"),
}


# ── OpenAI Codex (ChatGPT Plus/Pro subscription) ─────────────────────────
#
# When the user has logged into pi's `openai-codex` provider via
# ``/login`` (ChatGPT Plus/Pro), pi stores an OAuth access token in
# ``~/.pi/agent/auth.json``.  We can re-use that subscription from the
# decompile harness by routing pydantic-ai's :class:`OpenAIResponsesModel`
# at the Codex backend URL (``https://chatgpt.com/backend-api/codex``)
# and injecting the headers pi-mono's ``openai-codex-responses`` API
# layer sends: Authorization bearer, ``chatgpt-account-id``,
# ``originator``, and ``OpenAI-Beta: responses=experimental``.
#
# The Codex backend REJECTS ``store: true`` ("Store must be set to
# false") -- we force ``openai_store=False`` in :func:`build_agent`
# whenever the resolved model id has the ``openai-codex:`` prefix.
#
# Auth source-of-truth: pi-ai/dist/api/openai-codex-responses.js (the
# JS oracle this matches header-for-header).  Token refresh is handled
# by pi's UI on next ``/login``; we just read the cached access token.

_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
_CODEX_AUTH_PATH = Path.home() / ".pi" / "agent" / "auth.json"
_CODEX_JWT_CLAIM_PATH = "https://api.openai.com/auth"


def _load_codex_oauth() -> tuple[str, str]:
    """Read pi's ``openai-codex`` OAuth entry and return ``(access, accountId)``.

    Mirrors :func:`loadOpenAICodexOAuth` in pi-ai.  Raises a helpful
    :class:`RuntimeError` when the user hasn't run ``/login`` for the
    Codex provider yet.
    """
    if not _CODEX_AUTH_PATH.is_file():
        raise RuntimeError(
            f"openai-codex: no auth file at {_CODEX_AUTH_PATH}; run "
            "pi's `/login` and pick \"ChatGPT Plus/Pro (Codex)\" first."
        )
    try:
        blob = json.loads(_CODEX_AUTH_PATH.read_text())
        entry = blob["openai-codex"]
        if entry.get("type") != "oauth":
            raise KeyError("not oauth")
        access: str = entry["access"]
    except (KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "openai-codex: auth.json has no usable `openai-codex` OAuth "
            "entry; run pi's `/login` and pick \"ChatGPT Plus/Pro (Codex)\"."
        ) from exc

    # Prefer the explicit accountId field; fall back to decoding the JWT
    # (pi-ai's extractAccountId() does the same).  ChatGPT account id
    # lives at JWT claim ``https://api.openai.com/auth.chatgpt_account_id``.
    account_id = entry.get("accountId")
    if not account_id:
        try:
            payload_b64 = access.split(".")[1]
            # JWT base64url; add padding so stdlib base64 accepts it.
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            account_id = payload[_CODEX_JWT_CLAIM_PATH]["chatgpt_account_id"]
        except Exception as exc:
            raise RuntimeError(
                "openai-codex: could not extract chatgpt_account_id from "
                "the cached access token; re-run pi's `/login`."
            ) from exc
    return access, account_id


def _build_codex_model(model_name: str):
    """Return an :class:`OpenAIResponsesModel` wired at the ChatGPT
    Codex subscription backend.

    The custom :class:`openai.AsyncOpenAI` client points at
    ``https://chatgpt.com/backend-api/codex`` (so SDK calls to
    ``client.responses.create`` POST to ``…/codex/responses``) and
    carries the four header values the Codex backend requires.

    The OAuth access token is fed to the SDK as ``api_key=`` so the
    standard ``Authorization: Bearer <token>`` header is set.
    """
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    access, account_id = _load_codex_oauth()
    client = AsyncOpenAI(
        base_url=_CODEX_BASE_URL,
        api_key=access,
        default_headers={
            "chatgpt-account-id": account_id,
            "originator": "pi",
            "OpenAI-Beta": "responses=experimental",
            "User-Agent": "pi-c2-decompile",
        },
    )
    return OpenAIResponsesModel(
        model_name,
        provider=OpenAIProvider(openai_client=client),
    )


# Auto-fallback table for short-context models that share a provider
# with a long-context sibling.  When the user picks a SHORT model and
# we hit a context-overflow at runtime (HTTP 400 + a 'maximum context
# length' message in the body), pydantic-ai's ``FallbackModel`` rolls
# the SAME request over to the long-context sibling -- transparent to
# the orchestrator, only paid for when actually needed.
#
# Mapping: ``<resolved-id>: <sibling-id>``.  Both ids go through the
# normal ``_build_model`` resolver (so the sibling can be on a different
# endpoint table) -- this is a key in the FINAL id, not the user's CLI
# string.  Symmetric pairs are not added: starting from the long model
# does NOT auto-fallback to the short one (no reason to).
_AUTO_CONTEXT_FALLBACKS: dict[str, str] = {
    # GLM-5.2-short (200k) -> GLM-5.2 (1M); same neuralwatt endpoint.
    "neuralwatt:glm-5.2-short":      "neuralwatt:glm-5.2",
    "neuralwatt:glm-5.2-short-fast": "neuralwatt:glm-5.2-fast",
}


def _is_context_overflow(exc: Exception) -> bool:
    """Predicate for ``FallbackModel(fallback_on=…)``: True iff ``exc``
    is the provider's "prompt too long for context window" rejection.

    We deliberately scope this NARROWLY -- HTTP 400 with a body that
    names the context length.  A 400 for some OTHER reason (malformed
    tool schema, bad role sequence, …) is a real bug and must NOT
    silently flip providers; let it bubble up.
    """
    from pydantic_ai.exceptions import ModelHTTPError
    if not isinstance(exc, ModelHTTPError):
        return False
    if exc.status_code != 400:
        return False
    # Body shape varies across providers; check the rendered str (which
    # the ``ModelHTTPError.__init__`` builds as
    # ``f'status_code: {…}, model_name: {…}, body: {body}'``) for the
    # canonical phrases.  Cheap and provider-agnostic.
    blob = f"{exc.body}".lower()
    return any(p in blob for p in (
        "maximum context length",
        "context length",
        "context_length_exceeded",
        "prompt is too long",
        "too many tokens",
    ))


def _build_model(model_id: str, *, _resolving_fallback: bool = False):
    """Resolve ``model_id`` to a pydantic-ai Model instance.

    Pydantic-AI handles ``deepseek:`` / ``openai:`` / ``anthropic:`` /
    ``google:`` natively, each reading its provider-canonical env var.
    This function intercepts ids whose PREFIX names a custom endpoint
    — either OpenAI-compatible (:data:`_OPENAI_COMPAT_ENDPOINTS`) or
    Anthropic-compatible (:data:`_ANTHROPIC_COMPAT_ENDPOINTS`).

    ``_resolving_fallback`` is an internal flag: when True we skip the
    :data:`_AUTO_CONTEXT_FALLBACKS` lookup so the fallback model itself
    doesn't recursively wrap (it would loop on the same sibling).
    """
    # Auto-context-fallback: if the resolved id has a long-context
    # sibling, wrap the primary in ``FallbackModel`` so a context
    # overflow rolls the SAME request over transparently.  We do this
    # FIRST -- before any provider resolution -- so the wrapper sits
    # outside both providers' setup paths.
    if not _resolving_fallback and model_id in _AUTO_CONTEXT_FALLBACKS:
        from pydantic_ai.models.fallback import FallbackModel
        primary  = _build_model(model_id,                              _resolving_fallback=True)
        sibling  = _build_model(_AUTO_CONTEXT_FALLBACKS[model_id],     _resolving_fallback=True)
        return FallbackModel(primary, sibling, fallback_on=_is_context_overflow)

    if ":" not in model_id:
        return model_id
    prefix, name = model_id.split(":", 1)

    ow = _OPENAI_COMPAT_ENDPOINTS.get(prefix)
    if ow is not None:
        base_url, key_env = ow
        api_key = os.environ.get(key_env)
        if not api_key:
            raise RuntimeError(
                f"model {model_id!r} needs env var {key_env}; set it in "
                f".env (endpoint is OpenAI-compatible at {base_url})."
            )
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        return OpenAIChatModel(
            name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )

    if prefix == "openai-codex":
        # ChatGPT Plus/Pro subscription via pi's OAuth cache.
        return _build_codex_model(name)

    ant = _ANTHROPIC_COMPAT_ENDPOINTS.get(prefix)
    if ant is not None:
        base_url, key_env, key_default = ant
        api_key = os.environ.get(key_env, key_default)
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider
        # Retry transient failures (429 / 5xx / 529 overloaded / timeouts)
        # transparently at the SDK level -- no agent restart.  Default
        # max_retries=2 is too low under sustained proxy overload.  The
        # orchestrator adds a second retry layer for errors the proxy
        # passes through as a body rather than a retryable status.
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(base_url=base_url, api_key=api_key,
                                    max_retries=8)
            provider = AnthropicProvider(anthropic_client=client)
        except Exception:                       # noqa: BLE001
            provider = AnthropicProvider(base_url=base_url, api_key=api_key)
        return AnthropicModel(name, provider=provider)

    return model_id    # pydantic-ai resolves the rest


# ── agent builder ────────────────────────────────────────────────────────


def build_agent(
    *,
    target: Target,
    model_id: str = DEFAULT_MODEL_ID,
    max_tokens: Optional[int] = None,
    thinking: Optional[str] = None,
    model_override: object = None,
    extra_prompt: Optional[str] = None,
) -> Agent[AgentDeps, AgentFinishReport]:
    """Construct the decompile subagent for one function/target pair.

    The Agent is generic over ``AgentDeps`` (the per-run context passed
    via ``deps=…``) and :class:`AgentFinishReport` (the MINIMAL
    enforced output schema — verdict + reason + optional classification
    + optional next_suggested_tool).  The orchestrator later wraps this
    in the richer :class:`FinishReport` with workspace-observed truth
    for the verify/best fields, so the model is never asked to
    reconstruct nested data it doesn't reliably have in context.

    ``model_id`` is passed straight through to pydantic-ai's provider
    resolver.  Authentication is read from the standard provider env
    vars (``DEEPSEEK_API_KEY`` for DeepSeek, ``OPENAI_API_KEY`` for
    OpenAI, …) — set them in your shell or in a ``.env`` file in the
    project root.

    ``model_override``: a pydantic-ai Model instance to use instead of
    resolving ``model_id``.  Useful for tests (TestModel) and for
    callers that already have a configured Model in hand.
    """
    # Native pydantic-ai model resolution: ``deepseek:foo`` is read by
    # ``DeepSeekProvider`` (env var ``DEEPSEEK_API_KEY``), ``openai:foo``
    # by ``OpenAIProvider``, etc.  For OpenAI-compatible third-party
    # endpoints (``neuralwatt:``, ``requesty:`` …) ``_build_model``
    # wraps ``OpenAIChatModel`` with the right base_url.
    model = model_override if model_override is not None else _build_model(model_id)

    # Thinking-on-by-default for DeepSeek's reasoner-style routes is
    # handled by their model profile (always-on); for other providers
    # (Anthropic, OpenAI o-series) ``thinking`` selects the level.
    # Pydantic-AI takes ``thinking`` as one of ``'minimal' | 'low' |
    # 'medium' | 'high' | 'xhigh'`` or a bool, and routes it to each
    # provider's native reasoning channel (Anthropic extended thinking,
    # OpenAI reasoning_effort, etc.).
    model_settings: dict = {}
    # Anthropic REQUIRES max_tokens on every request and pydantic-ai's
    # built-in default is a stingy 4096 — fine for a chat turn, but a
    # thinking-on Opus run routinely burns 8-30k tokens INSIDE the
    # <thinking> channel before a single visible word, blowing the
    # 4096 cap and aborting with "token limit exceeded before any
    # response was generated".  We choose a generous default that
    # leaves headroom for extended thinking + tool-call generation +
    # the structured FinishReport.  Larger when thinking is enabled.
    # Allow ``--thinking none|off|no`` (and empty) to disable thinking.
    if isinstance(thinking, str) and thinking.strip().lower() in (
            "none", "off", "no", "disable", "disabled", ""):
        thinking = None
    is_codex = isinstance(model_id, str) and model_id.startswith("openai-codex:")
    if max_tokens is None:
        max_tokens = 32_000 if thinking else 16_000
    # The ChatGPT Codex backend rejects ``max_output_tokens`` outright
    # ("Unsupported parameter: max_output_tokens"); skip the cap entirely
    # for codex runs.  Everywhere else we keep our generous default so
    # extended thinking + tool calls have room to breathe.
    if not is_codex:
        model_settings["max_tokens"] = max_tokens
    if thinking is not None:
        model_settings["thinking"] = thinking

    # ChatGPT Codex backend rejects ``store: true`` ("Store must be set
    # to false").  Force the OpenAIResponsesModel to send ``store=false``
    # whenever this run is going through pi's openai-codex subscription.
    if is_codex:
        model_settings.setdefault("openai_store", False)

    agent: Agent[AgentDeps, AgentFinishReport] = Agent(
        model,
        deps_type=AgentDeps,
        output_type=AgentFinishReport,
        system_prompt=system_prompt(target, extra_prompt),
        model_settings=model_settings or None,
        # AgentFinishReport is intentionally minimal (4 flat fields), so
        # 3 retries is plenty.  The orchestrator also has a verdict
        # promotion path that reconstructs the right verdict from the
        # workspace's best snapshot when the model fails entirely, so a
        # blown retry budget is no longer catastrophic.
        retries=3,
    )

    # Register every tool.  The decorator versions auto-detect the
    # ``ctx: RunContext[AgentDeps]`` parameter and pass deps through.
    # No bootstrap tool: the orchestrator composes the workspace BEFORE
    # the agent runs and embeds the function brief in the initial user
    # message, so the agent's first turn can already be productive
    # (verify / read / edit) instead of mechanical workspace setup.
    agent.tool(tools.read)
    agent.tool(tools.write)
    agent.tool(tools.edit)
    agent.tool(tools.verify)
    agent.tool(tools.revert_to_best)
    agent.tool(tools.disasm)
    agent.tool(tools.decompile)
    agent.tool(tools.info)
    agent.tool(tools.nearest)
    agent.tool(tools.fetch)
    agent.tool(tools.lookup)
    agent.tool(tools.regtrace)
    agent.tool(tools.census)
    agent.tool(tools.lines)
    agent.tool(tools.search)
    # trace-level spelling tools (instrumented-compiler backed; ~15 s per
    # trace).  spell/suggest screen WITHOUT byte compiles; fusion/
    # walk_order are the rover / chain-structure diagnosis views.
    agent.tool(tools.spell)
    agent.tool(tools.suggest)
    agent.tool(tools.fusion)
    agent.tool(tools.walk_order)

    return agent
