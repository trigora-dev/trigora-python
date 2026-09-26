from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from trigora_client import Client, start


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
