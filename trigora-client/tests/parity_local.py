"""Run the local /v1 sequence against a trigora dev server."""

import json
import os
import sys

from trigora_client import Client, TrigoraError


def main() -> None:
    url = os.environ["TRIGORA_PARITY_URL"]
    body = json.loads(os.environ["TRIGORA_PARITY_BODY"])
    client = Client(url=url)
    projects = client.projects.list()["projects"]
    assert any(project["slug"] == "default" for project in projects)
    created = client.projects.create({"name": "parity-python"})
    assert created["project"]["name"] == "parity-python"
    deployed = client.deploy(body)
    assert deployed["program"]["name"] == body["name"]
    assert deployed["version"]["artifactHash"] == body["artifact"]["hash"]
    listed = client.programs.list()["programs"]
    assert any(program["name"] == body["name"] for program in listed)
    program = client.programs.get(body["name"])["program"]
    assert program["currentVersion"]["artifactHash"] == body["artifact"]["hash"]
    versions = client.programs.versions(body["name"])["versions"]
    assert any(version["artifactHash"] == body["artifact"]["hash"] for version in versions)
    first = client.executions.start(body["name"], {})
    first.send("approved", {"ok": True})
    assert first.result() == {"ok": True, "approval": {"ok": True}}
    second = client.executions.start(body["name"], {})
    second.cancel()
    try:
        second.result()
    except TrigoraError as error:
        assert "cancelled" in str(error)
    else:
        raise AssertionError("cancelled execution should fail result()")


if __name__ == "__main__":
    main()
    sys.stdout.write("python parity ok\n")
