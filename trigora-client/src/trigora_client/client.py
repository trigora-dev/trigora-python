from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_RUNTIME_URL = "http://127.0.0.1:3477"
DEFAULT_CLOUD_API_URL = "https://api.trigora.dev"
_PROJECT_HEADER = "X-Trigora-Project-Id"


class TrigoraError(RuntimeError):
    def __init__(self, message: str, *, status: int = 0, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def _base_url(url: str | None, token: str | None) -> str:
    if url:
        return url.rstrip("/")
    if token:
        return (os.environ.get("TRIGORA_API_BASE_URL") or DEFAULT_CLOUD_API_URL).rstrip("/")
    return (os.environ.get("TRIGORA_RUNTIME_URL") or DEFAULT_RUNTIME_URL).rstrip("/")


class Client:
    def __init__(
        self,
        *,
        url: str | None = None,
        token: str | None = None,
        project_id: str | None = None,
    ) -> None:
        resolved_token = (
            token if token is not None else os.environ.get("TRIGORA_TOKEN", "").strip() or None
        )
        self.url = _base_url(url, resolved_token)
        self.token = resolved_token
        self.project_id = project_id
        self.projects = Projects(self)
        self.programs = Programs(self)
        self.executions = Executions(self)

    def whoami(self) -> dict[str, Any]:
        return self._request("GET", "/v1/whoami")

    def deploy(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/programs/deploy", body)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
    ) -> Any:
        target = f"{self.url}{path}"
        if query:
            target = f"{target}?{urllib.parse.urlencode(query)}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.project_id:
            headers[_PROJECT_HEADER] = self.project_id
        request = urllib.request.Request(target, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8")
            message = raw or str(error)
            code = None
            try:
                parsed = json.loads(raw)
                message = parsed.get("error", {}).get("message") or message
                code = parsed.get("error", {}).get("code")
            except json.JSONDecodeError:
                pass
            raise TrigoraError(message, status=error.code or 0, code=code) from error
        except urllib.error.URLError as error:
            raise TrigoraError(
                f"Could not reach Trigora at {target}. {error.reason}",
                status=0,
            ) from error


class Projects:
    def __init__(self, client: Client) -> None:
        self._client = client

    def list(self) -> dict[str, Any]:
        return self._client._request("GET", "/v1/projects")

    def create(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._client._request("POST", "/v1/projects", body)


class Programs:
    def __init__(self, client: Client) -> None:
        self._client = client

    def list(self, *, limit: int | None = None, cursor: str | None = None) -> dict[str, Any]:
        return self._client._request("GET", "/v1/programs", query=_page(limit, cursor))

    def get(self, program_id: str) -> dict[str, Any]:
        return self._client._request("GET", f"/v1/programs/{urllib.parse.quote(program_id)}")

    def versions(
        self, program_id: str, *, limit: int | None = None, cursor: str | None = None
    ) -> dict[str, Any]:
        return self._client._request(
            "GET",
            f"/v1/programs/{urllib.parse.quote(program_id)}/versions",
            query=_page(limit, cursor),
        )


class Executions:
    def __init__(self, client: Client) -> None:
        self._client = client

    def start(self, program_id: str, input: Any | None = None) -> ExecutionHandle:
        body = self._client._request(
            "POST",
            "/v1/executions",
            {"programId": program_id, "input": {} if input is None else input},
        )
        return ExecutionHandle(self._client, body["execution"]["id"])

    def get(self, execution_id: str) -> dict[str, Any]:
        body = self._client._request("GET", f"/v1/executions/{urllib.parse.quote(execution_id)}")
        return body["execution"]

    def list(self, *, limit: int | None = None, cursor: str | None = None) -> dict[str, Any]:
        return self._client._request("GET", "/v1/executions", query=_page(limit, cursor))

    def send(self, execution_id: str, name: str, payload: Any = None) -> dict[str, Any]:
        return self._client._request(
            "POST",
            f"/v1/executions/{urllib.parse.quote(execution_id)}/events",
            {"name": name, "payload": {} if payload is None else payload},
        )

    def cancel(self, execution_id: str) -> dict[str, Any]:
        return self._client._request(
            "POST",
            f"/v1/executions/{urllib.parse.quote(execution_id)}/cancel",
            {},
        )

    def result(self, execution_id: str, *, poll_seconds: float = 0.05) -> Any:
        return ExecutionHandle(self._client, execution_id).result(poll_seconds=poll_seconds)


class ExecutionHandle:
    def __init__(self, client: Client, execution_id: str) -> None:
        self._client = client
        self.id = execution_id

    def send(self, name: str, payload: Any = None) -> None:
        self._client.executions.send(self.id, name, payload)

    def cancel(self) -> None:
        self._client.executions.cancel(self.id)

    def result(self, *, poll_seconds: float = 0.05) -> Any:
        while True:
            execution = self._client.executions.get(self.id)
            status = execution["status"]
            if status == "completed":
                return execution.get("result")
            if status == "failed":
                error = execution.get("error") or {}
                raise TrigoraError(error.get("message") or "Execution failed.")
            if status == "cancelled":
                raise TrigoraError(f'Execution "{self.id}" was cancelled.', status=409)
            time.sleep(poll_seconds)


def start(
    program_id: str, input: Any | None = None, *, url: str | None = None, token: str | None = None
) -> ExecutionHandle:
    return Client(url=url, token=token).executions.start(program_id, input)


def _page(limit: int | None, cursor: str | None) -> dict[str, str] | None:
    query: dict[str, str] = {}
    if limit is not None:
        query["limit"] = str(limit)
    if cursor:
        query["cursor"] = cursor
    return query or None
