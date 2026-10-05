from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

from trigora_client import Client, TrigoraError, start


class Handler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict[str, str | None]]] = []

    def do_GET(self) -> None:
        self.requests.append(
            {"path": self.path.split("?", 1)[0], "authorization": self.headers.get("Authorization")}
        )
        if self.path == "/v1/whoami":
            self._json(200, {"actorType": "api_token"})
            return
        if self.path.startswith("/v1/programs/approval/versions"):
            self._json(200, {"versions": [{"id": "ver_1", "artifactHash": "abc"}]})
            return
        if self.path.startswith("/v1/executions/exec_1"):
            self._json(
                200,
                {"execution": {"id": "exec_1", "status": "completed", "result": {"ok": True}}},
            )
            return
        self._json(404, {"error": {"message": "missing", "code": "not_found"}})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw) if raw else {}
        if self.path == "/v1/executions":
            self._json(200, {"execution": {"id": "exec_1", "programId": body["programId"]}})
            return
        if self.path.endswith("/events"):
            self._json(200, {"ok": True, "name": body["name"]})
            return
        self._json(404, {"error": {"message": "missing"}})

    def _json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address[:2]
        cls.url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def test_start_send_and_result(self) -> None:
        run = start("approval", {"n": 1}, url=self.url)
        self.assertEqual(run.id, "exec_1")
        run.send("approved", "ok")
        self.assertEqual(run.result(), {"ok": True})

    def test_whoami(self) -> None:
        client = Client(url=self.url)
        self.assertEqual(client.whoami()["actorType"], "api_token")

    def test_program_versions(self) -> None:
        client = Client(url=self.url)
        versions = client.programs.versions("approval", limit=1)
        self.assertEqual(versions["versions"][0]["id"], "ver_1")

    def test_env_token_stays_local_without_authorization(self) -> None:
        with _env(TRIGORA_TOKEN="cloud-token"):
            os.environ.pop("TRIGORA_RUNTIME_URL", None)
            client = Client()
            self.assertEqual(client.url, "http://127.0.0.1:3477")
            self.assertIsNone(client.token)
            os.environ["TRIGORA_RUNTIME_URL"] = self.url
            Handler.requests.clear()
            Client().whoami()
        self.assertIsNone(Handler.requests[-1]["authorization"])

    def test_remote_selects_cloud_and_sends_token(self) -> None:
        with _env(TRIGORA_TOKEN="cloud-token"):
            os.environ.pop("TRIGORA_API_BASE_URL", None)
            client = Client(remote=True)
            self.assertEqual(client.url, "https://api.trigora.dev")
            self.assertEqual(client.token, "cloud-token")
        with _env(TRIGORA_TOKEN="cloud-token", TRIGORA_API_BASE_URL=self.url):
            Handler.requests.clear()
            Client(remote=True).whoami()
        self.assertEqual(Handler.requests[-1]["authorization"], "Bearer cloud-token")

    def test_remote_without_token_fails_at_construction(self) -> None:
        with _env():
            os.environ.pop("TRIGORA_TOKEN", None)
            with self.assertRaises(TrigoraError) as caught:
                Client(remote=True)
        self.assertIn("TRIGORA_TOKEN is not set", str(caught.exception))

    def test_explicit_url_wins_over_remote_without_a_token(self) -> None:
        with _env():
            os.environ.pop("TRIGORA_TOKEN", None)
            Handler.requests.clear()
            client = Client(url=self.url, remote=True)
            self.assertEqual(client.url, self.url)
            client.whoami()
        self.assertIsNone(Handler.requests[-1]["authorization"])

    def test_explicit_token_is_sent_to_a_custom_local_url(self) -> None:
        with _env(TRIGORA_TOKEN="env-token"):
            Handler.requests.clear()
            Client(url=self.url, token="explicit-token", remote=False).whoami()
        self.assertEqual(Handler.requests[-1]["authorization"], "Bearer explicit-token")


class _env:
    def __init__(self, **values: str) -> None:
        self.values = values
        self.previous: dict[str, str | None] = {}

    def __enter__(self) -> None:
        keys = set(self.values) | {"TRIGORA_TOKEN", "TRIGORA_RUNTIME_URL", "TRIGORA_API_BASE_URL"}
        for key in keys:
            self.previous[key] = os.environ.get(key)
        for key, value in self.values.items():
            os.environ[key] = value

    def __exit__(self, *_args: object) -> None:
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
