# trigora-client

Python client for starting and controlling Trigora executions. Import it as `trigora_client`.

```python
from trigora_client import Client

client = Client()
run = client.executions.start("approval", {})
run.send("approved", "ok")
print(run.result())
```

`Client()` uses `TRIGORA_TOKEN` to talk to Trigora Cloud (`TRIGORA_API_BASE_URL`, default `https://api.trigora.dev`). Without a token it uses the local runtime (`TRIGORA_RUNTIME_URL`, default `http://127.0.0.1:3477`).

The same client can call `whoami`, `projects`, `deploy`, and `programs`, including `programs.versions`. Triggers are configured in `trigora.toml` and deployed with the Trigora CLI. They are not SDK or client APIs.
