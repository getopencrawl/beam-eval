"""Every OpenCrawl call the harness makes, against a self-hosted opencrawl-core stack
(deploy/compose.yaml: receiver -> S3 -> Temporal indexing worker -> OpenSearch -> MCP).

- Ingest uses the session capture API, the same endpoint the `opencrawl collect` CLI uploads to:
  POST /api/sessions/batches. One BEAM conversation is one captured session; each turn is one
  `message` event carrying the role, text, ordinal and the turn's date, exactly as a captured
  Claude Code transcript would carry them.
- Indexing is the product's own Temporal sweep. The harness only triggers the schedule early
  (deploy/trigger-index.mjs) and waits until OpenSearch holds one first chunk per event.
- Retrieval goes through the MCP server's `search` and `fetch` tools (the agent-facing product
  surface), restricted to the conversation's session with the product's own `sessionId` filter so
  that conversations stay isolated from each other.

Environment: OPENCRAWL_DEPLOY_DIR (the core checkout's deploy/ directory, holding .env).
"""

import asyncio
import json
import os
from pathlib import Path

import httpx

from log import log

# A batch holds at most 1,000 events and 16 MiB; stay well inside both.
EVENTS_PER_BATCH = 500
MAX_BATCH_BYTES = 12 * 1024 * 1024
WAITS_BETWEEN_TRIES = (1, 2, 4, 8)  # seconds; five tries in all
TIMEOUT_SECONDS = 120
INSTALLATION = "beam-benchmark"


class OpenCrawlError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def deploy_dir() -> Path:
    return Path(os.environ.get("OPENCRAWL_DEPLOY_DIR", "")).expanduser()


def read_env() -> dict[str, str]:
    env = {}
    for line in (deploy_dir() / ".env").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    return env


# v3 (beam3-): passage-level indexing (core PR #137). v2 sessions space turns one millisecond apart (OpenSearch dates keep milliseconds), so a
# question's as-of moment separates every turn; v1 ("beam-") spaced them by microseconds.
SESSION_PREFIX = "beam3"


def session_id(split: str, conversation_id: str) -> str:
    return f"{SESSION_PREFIX}-{split}-{conversation_id}"


class OpenCrawl:
    def __init__(self) -> None:
        env = read_env()
        self.receiver = f"http://127.0.0.1:{env.get('OPENCRAWL_SESSIONS_PORT', '8093')}"
        self.mcp_url = f"http://127.0.0.1:{env.get('OPENCRAWL_MCP_PORT', '8094')}/mcp"
        limits = httpx.Limits(max_connections=64, max_keepalive_connections=64)
        self._capture = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {env['OPENCRAWL_SESSIONS_TOKEN']}"},
            timeout=TIMEOUT_SECONDS,
            limits=limits,
        )
        self._mcp = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {env['MCP_TOKEN']}", "Accept": "application/json, text/event-stream"},
            timeout=TIMEOUT_SECONDS,
            limits=limits,
        )
        self._mcp_session: str | None = None
        self._mcp_lock = asyncio.Lock()
        self._request_id = 0
        self.principal: dict | None = None

    async def close(self) -> None:
        await self._capture.aclose()
        await self._mcp.aclose()

    # --- Capture ---------------------------------------------------------------------------

    async def identity(self) -> dict:
        data = await self._capture_call("GET", "/api/sessions/identity")
        self.principal = data["principal"]
        return self.principal

    async def ingest(self, session: str, events: list[dict]) -> int:
        """Uploads every event in order; returns the number of batches stored."""
        if self.principal is None:
            await self.identity()
        owner = {"tenantId": self.principal["tenantId"], "userId": self.principal["userId"]}
        stored = 0
        for batch in _batches(events):
            receipt = await self._capture_call(
                "POST",
                "/api/sessions/batches",
                {
                    "schemaVersion": 1,
                    "owner": owner,
                    "harness": "claude-code",
                    "origin": "cli",
                    "captureMode": "history",
                    "installationId": INSTALLATION,
                    "sessionId": session,
                    "attachments": [],
                    "events": batch,
                },
            )
            if not receipt.get("stored") and not receipt.get("batchId"):
                raise OpenCrawlError(f"Batch for {session} was not stored: {receipt}")
            stored += 1
        return stored

    async def _capture_call(self, method: str, path: str, body: dict | None = None) -> dict:
        for wait in (*WAITS_BETWEEN_TRIES, None):  # None marks the last try
            try:
                response = await self._capture.request(method, self.receiver + path, json=body)
                if response.status_code < 500 and response.status_code != 429:
                    payload = response.json()
                    if response.is_error:
                        raise OpenCrawlError(
                            f"{path}: {response.status_code} {payload.get('error')}", status=response.status_code
                        )
                    return payload["data"]
                error = OpenCrawlError(
                    f"{path}: {response.status_code} {response.text[:300]}", status=response.status_code
                )
            except httpx.HTTPError as caught:
                error = caught
            if wait is None:
                raise error
            await asyncio.sleep(wait)
        raise AssertionError("the last try returns or raises")

    # --- Indexing --------------------------------------------------------------------------

    async def trigger_indexing(self) -> None:
        """Runs the product's indexing schedule now instead of at its next 5-minute tick."""
        await _compose("exec", "-T", "worker", "node", "deploy/trigger-index.mjs")

    async def indexed_events(self, session: str) -> int:
        """Events of a session that OpenSearch can return: one first chunk per indexed event."""
        query = json.dumps(
            {"query": {"bool": {"filter": [{"term": {"session.sessionId": session}}, {"term": {"session.chunk": 0}}]}}}
        )
        out = await _compose(
            "exec",
            "-T",
            "opensearch",
            "curl",
            "-s",
            "-H",
            "content-type: application/json",
            "localhost:9200/opencrawl-*/_count",
            "-d",
            query,
        )
        return int(json.loads(out).get("count", 0))

    # --- MCP: search and fetch -------------------------------------------------------------

    async def tools(self) -> list[dict]:
        return (await self._rpc("tools/list", {}))["tools"]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """The tool's structured result, or {"error": text} when the tool reports an error."""
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        text = "".join(part.get("text", "") for part in result.get("content", []) if isinstance(part, dict))
        if result.get("isError"):
            return {"error": text}
        return result.get("structuredContent") or json.loads(text)

    async def search(
        self,
        session: str,
        query: str,
        limit: int = 40,
        match: str = "any",
        cursor: str | None = None,
        before: str | None = None,
        source: str = "sessions",
        order: str | None = None,
        role: str | None = None,
        collapse: bool = False,
    ) -> dict:
        arguments = {"query": query[:4000], "source": source, "sessionId": session, "match": match, "limit": limit}
        if before:
            arguments["before"] = before
        if order:
            arguments["order"] = order
        if role:
            arguments["role"] = role
        if collapse:
            arguments["collapse"] = True
        if cursor:
            arguments["cursor"] = cursor
        return await self.call_tool("search", arguments)

    async def fetch(self, passage_id: str, offset: int = 0, length: int = 6000) -> dict:
        return await self.call_tool("fetch", {"id": passage_id, "offset": offset, "length": length})

    async def _initialize(self) -> None:
        response = await self._mcp.post(
            self.mcp_url,
            json={
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "beam-benchmark", "version": "1"},
                },
            },
        )
        response.raise_for_status()
        self._mcp_session = response.headers.get("mcp-session-id")
        headers = {"mcp-session-id": self._mcp_session} if self._mcp_session else {}
        await self._mcp.post(
            self.mcp_url, headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"}
        )

    async def _rpc(self, method: str, params: dict) -> dict:
        for wait in (*WAITS_BETWEEN_TRIES, None):
            try:
                async with self._mcp_lock:
                    if self._mcp_session is None:
                        await self._initialize()
                    self._request_id += 1
                    request_id = self._request_id
                headers = {"mcp-session-id": self._mcp_session} if self._mcp_session else {}
                response = await self._mcp.post(
                    self.mcp_url,
                    headers=headers,
                    json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                )
                if response.status_code in (400, 404) and "session" in response.text.lower():
                    self._mcp_session = None  # the server forgot the session; start a new one
                    raise OpenCrawlError(f"MCP session expired: {response.text[:200]}")
                response.raise_for_status()
                message = _rpc_message(response, request_id)
                if "error" in message:
                    raise OpenCrawlError(f"MCP {method} error: {message['error']}")
                return message["result"]
            except (httpx.HTTPError, OpenCrawlError) as error:
                if wait is None:
                    raise
                log(f"MCP {method} failed ({str(error)[:120]}); retrying")
                await asyncio.sleep(wait)
        raise AssertionError("the last try returns or raises")


def _rpc_message(response: httpx.Response, request_id: int) -> dict:
    """A JSON-RPC reply, sent either as JSON or as a server-sent event stream."""
    if "text/event-stream" in response.headers.get("content-type", ""):
        for line in response.text.splitlines():
            if line.startswith("data:"):
                message = json.loads(line[5:].strip())
                if message.get("id") == request_id:
                    return message
        raise OpenCrawlError("MCP stream ended without a reply")
    return response.json()


def _batches(events: list[dict]) -> list[list[dict]]:
    result, batch, size = [], [], 0
    for event in events:
        event_bytes = len(json.dumps(event, ensure_ascii=False).encode())
        if batch and (len(batch) == EVENTS_PER_BATCH or size + event_bytes > MAX_BATCH_BYTES):
            result.append(batch)
            batch, size = [], 0
        batch.append(event)
        size += event_bytes
    if batch:
        result.append(batch)
    return result


async def _compose(*args: str) -> str:
    process = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "-f",
        str(deploy_dir() / "compose.yaml"),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate()
    if process.returncode != 0:
        raise OpenCrawlError(f"docker compose {' '.join(args[:3])} failed: {err.decode()[:300]}")
    return out.decode()
