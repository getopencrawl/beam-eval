"""The model calls of the harness.

One model answers the questions and judges the answers: gpt-5.6-luna with reasoning off, called through OpenAI's
Chat Completions API with a single user message and no system prompt. Memory-writing passes (notes.py, facts.py,
conflicts.py) and retrieval-side helpers use the same client and may ask for another reasoning effort; answers and
verdicts never do unless an environment variable below says so.

Environment:
    OPENAI_API_KEY            required
    BEAM_LLM_CONCURRENCY      requests in flight at once (default 24)
    BEAM_ANSWER_TEMPERATURE   temperature of the answer call on the default route (default: the provider's);
                              the "responses" and "openrouter" routes do not send it
    BEAM_ANSWER_REASONING     reasoning effort of the answer call (default "none")
    BEAM_ANSWER_API           "chat" (default), "responses" (OpenAI's Responses API) or "openrouter"
    BEAM_JUDGE_API            "chat" (default) or "openrouter"
    OPENROUTER_API_KEY        required for the two "openrouter" settings
    BEAM_OPENROUTER_RPM       OpenRouter requests started per minute (default 18)

The "openrouter" settings exist for one check: whether sending the same call through an API router, as some
published BEAM runs do, changes the scores. The request is then model "openai/gpt-5.6-luna", reasoning
{"effort": "none"}, usage accounting on, one user message, and for verdicts the strict JSON schema with
provider.require_parameters.

Failures. A request is tried up to four times when the failure may pass: a rate limit (429), a server error, a
dropped connection, an HTTP body that is not JSON. Anything else fails at once, and so does a reply that arrives
but is empty or, where an object was asked for, holds none. The caller then scores the question or the verdict 0
and records the error. A refusal of the account by the model service (401, 402, 403) stops the run instead, since
it would otherwise score everything 0. Other mistakes of configuration are not recognised as such: with a model
name the service does not know, a run completes with every question failed, which its summary shows as
failedQuestions.
"""

import asyncio
import json
import os
from dataclasses import dataclass

import httpx

from log import log

MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "none"
ROUTER_MODEL = "openai/gpt-5.6-luna"

CALLS_AT_ONCE = int(os.environ.get("BEAM_LLM_CONCURRENCY", "24"))
ANSWER_TEMPERATURE = float(os.environ["BEAM_ANSWER_TEMPERATURE"]) if os.environ.get("BEAM_ANSWER_TEMPERATURE") else None
ANSWER_REASONING = os.environ.get("BEAM_ANSWER_REASONING") or None
ANSWER_API = os.environ.get("BEAM_ANSWER_API") or "chat"
JUDGE_API = os.environ.get("BEAM_JUDGE_API") or "chat"
if ANSWER_API not in ("chat", "responses", "openrouter") or JUDGE_API not in ("chat", "openrouter"):
    raise RuntimeError(f"BEAM_ANSWER_API={ANSWER_API!r}, BEAM_JUDGE_API={JUDGE_API!r}: see the values at the top of llm.py")
ROUTER_REQUESTS_PER_MINUTE = float(os.environ.get("BEAM_OPENROUTER_RPM", "18"))

TIMEOUT_SECONDS = 90
BACKOFF_SECONDS = (2, 8, 30)  # waits between the four tries

# Tokens and calls of this process by purpose ("answer", "judge", "expand", ...); run.py writes them to usage.json.
USAGE: dict[str, dict] = {}


class ModelError(RuntimeError):
    """A request the service answered with a failure. `status` is the HTTP status when there was one."""

    def __init__(self, message: str, *, retryable: bool, status: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status = status


def stops_the_run(error: BaseException) -> bool:
    """True when the service refuses the account (wrong key, no credit, no access) rather than one request."""
    return getattr(error, "status", None) in (401, 402, 403)


# --- The three calls the harness makes --------------------------------------------------------------


async def complete_text(prompt: str, purpose: str = "answer", reasoning: str | None = None, model: str | None = None) -> str:
    """The reply to one user message, as text. An empty reply is an error."""
    answering = purpose == "answer"
    effort = reasoning or (ANSWER_REASONING if answering and ANSWER_REASONING else REASONING_EFFORT)
    if answering and ANSWER_API == "openrouter":
        text = _message_text(await _send(OPENROUTER, "/chat/completions", _router_request(prompt, effort), purpose))
    elif answering and ANSWER_API == "responses":
        request = {"model": model or MODEL, "reasoning": {"effort": effort}, "input": prompt}
        text = _responses_text(await _send(OPENAI, "/responses", request, purpose))
    else:
        request = _chat_request(prompt, model or MODEL, effort)
        if answering and ANSWER_TEMPERATURE is not None:
            request["temperature"] = ANSWER_TEMPERATURE
        text = _message_text(await _send(OPENAI, "/chat/completions", request, purpose))
    if not text.strip():
        raise ValueError("The model returned an empty answer")
    return text


async def complete_json(
    prompt: str, schema: dict, purpose: str = "judge", model: str | None = None, reasoning: str | None = None
) -> dict:
    """The reply to one user message as an object with exactly the fields of `schema` (a strict JSON schema)."""
    if purpose == "judge" and JUDGE_API == "openrouter":
        request = _router_request(prompt, REASONING_EFFORT)
        request["response_format"] = _strict_format(schema)
        request["provider"] = {"require_parameters": True}
        reply = await _send(OPENROUTER, "/chat/completions", request, purpose)
    else:
        request = _chat_request(prompt, model or MODEL, reasoning or REASONING_EFFORT)
        request["response_format"] = _strict_format(schema)
        reply = await _send(OPENAI, "/chat/completions", request, purpose)
    return _parse_object(_message_text(reply))


async def chat(messages: list[dict], tools: list[dict] | None = None, purpose: str = "agent", tool_choice: str = "auto") -> dict:
    """One turn of a conversation that may call tools: the assistant message, with any tool calls."""
    request = {"model": MODEL, "reasoning_effort": REASONING_EFFORT, "messages": messages}
    if tools:
        request["tools"] = tools
        request["tool_choice"] = tool_choice
    reply = await _send(OPENAI, "/chat/completions", request, purpose)
    return reply["choices"][0]["message"]


async def close() -> None:
    for connection in _connections.values():
        await connection.aclose()
    _connections.clear()


# --- Requests ---------------------------------------------------------------------------------------


def _chat_request(prompt: str, model: str, effort: str) -> dict:
    return {"model": model, "reasoning_effort": effort, "messages": [{"role": "user", "content": prompt}]}


def _router_request(prompt: str, effort: str) -> dict:
    return {
        "model": ROUTER_MODEL,
        "reasoning": {"effort": effort},
        "usage": {"include": True},
        "messages": [{"role": "user", "content": prompt}],
    }


def _strict_format(schema: dict) -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "benchmark_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": schema["properties"],
                "required": schema["required"],
                "additionalProperties": False,
            },
        },
    }


# --- Replies ----------------------------------------------------------------------------------------


def _message_text(reply: dict) -> str:
    content = reply["choices"][0]["message"]["content"]
    if content is None:
        return ""
    if isinstance(content, list):  # content given in parts
        return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return str(content)


def _responses_text(reply: dict) -> str:
    return "".join(
        part.get("text", "")
        for item in reply.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )


def _parse_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        first, last = text.find("{"), text.rfind("}")
        if 0 <= first < last:  # an object with words around it still counts
            return json.loads(text[first : last + 1])
        raise


# --- Transport --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Service:
    name: str
    url: str
    key_variable: str


OPENAI = _Service("OpenAI", "https://api.openai.com/v1", "OPENAI_API_KEY")
OPENROUTER = _Service("OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY")

_connections: dict[str, httpx.AsyncClient] = {}
_slots: asyncio.Semaphore | None = None
_router_gate: asyncio.Lock | None = None
_router_next_start = 0.0


def _connection(service: _Service) -> httpx.AsyncClient:
    if service.name not in _connections:
        key = os.environ.get(service.key_variable, "").strip()
        if not key:
            raise RuntimeError(f"{service.key_variable} is required")
        _connections[service.name] = httpx.AsyncClient(
            base_url=service.url, headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT_SECONDS
        )
    return _connections[service.name]


async def _router_turn() -> None:
    """Spaces the starts of OpenRouter requests evenly (new accounts are limited to 20 a minute for this model)."""
    global _router_gate, _router_next_start
    if _router_gate is None:
        _router_gate = asyncio.Lock()
    async with _router_gate:
        now = asyncio.get_running_loop().time()
        wait = max(0.0, _router_next_start - now)
        _router_next_start = max(now, _router_next_start) + 60.0 / ROUTER_REQUESTS_PER_MINUTE
    if wait:
        await asyncio.sleep(wait)


async def _send(service: _Service, path: str, request: dict, purpose: str) -> dict:
    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(CALLS_AT_ONCE)
    tries = len(BACKOFF_SECONDS) + 1
    for attempt in range(1, tries + 1):
        try:
            async with _slots:
                reply = await _send_once(service, path, request)
        except (httpx.HTTPError, ModelError, ValueError) as error:
            may_pass = error.retryable if isinstance(error, ModelError) else True
            if not may_pass or attempt == tries:
                raise
            pause = BACKOFF_SECONDS[attempt - 1]
            log(f"model call failed ({str(error)[:120]}); retrying in {pause}s")
            await asyncio.sleep(pause)
        else:
            _count(service, purpose, reply)
            return reply
    raise AssertionError("the loop above returns or raises")


async def _send_once(service: _Service, path: str, request: dict) -> dict:
    connection = _connection(service)
    if service is OPENROUTER:
        await _router_turn()
    response = await connection.post(path, json=request)
    if response.is_error:
        status = response.status_code
        raise ModelError(
            f"{service.name} returned {status}: {response.text[:1_000]}", retryable=status == 429 or status >= 500, status=status
        )
    reply = response.json()  # a body that is not JSON raises ValueError, which is tried again
    if path == "/responses":
        if not isinstance(reply, dict) or reply.get("error"):
            raise ModelError(f"{service.name} returned an error: {str(reply)[:300]}", retryable=False)
        return reply
    if not isinstance(reply, dict):
        raise ModelError(f"{service.name} returned a non-object response", retryable=True)
    if reply.get("error"):
        raise ModelError(f"{service.name} returned an error: {reply['error']}", retryable=False)
    if not isinstance(reply.get("choices"), list) or not reply["choices"]:
        raise ModelError(f"{service.name} returned no choices", retryable=False)
    return reply


def _count(service: _Service, purpose: str, reply: dict) -> None:
    used = reply.get("usage") or {}
    total = USAGE.setdefault(purpose, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
    total["calls"] += 1
    total["prompt_tokens"] += int(used.get("prompt_tokens") or used.get("input_tokens") or 0)
    total["completion_tokens"] += int(used.get("completion_tokens") or used.get("output_tokens") or 0)
    if service is OPENROUTER:  # the router also reports what the call cost and which provider served it
        total["openrouter_cost"] = round(total.get("openrouter_cost", 0.0) + float(used.get("cost") or 0.0), 6)
        provider = str(reply.get("provider"))
        served = total.setdefault("openrouter_providers", {})
        served[provider] = served.get(provider, 0) + 1
