# Trigora Python SDK and Client

Python authoring package for Trigora programs.

```python
from trigora import effect, program, wait_for_event


@program
async def approval():
    result = await effect("generate", lambda: 42)
    review = await wait_for_event("approved")
    return {"result": result, "review": review}
```

`gather` and `race` are durable joins. They are markers, like `effect`: calling them outside an execution throws.

The program entry is one `@program` async function. Start input is an ordered argument list of plain parameters. Defaults are compile-time constants (`None`, bool, finite number, string). Extra arguments are a start error. A bare `async def run` is not an entry. `from trigora import program as marker` is the same marker.

Discover programs from `trigora.toml`:

```toml
[project]
name = "my-project"
programs = ["src/**/*.py"]
```

Installing this package also installs the compatible TCC compiler and the `trigora` command from `trigora-cli`. This package does not ship that binary. The command is the Python ecosystem's CLI: it runs Python programs. The core CLI can run another language when that language's adapter and toolchain are already present. The markers themselves do not run the engine: calling one outside an execution throws, and `program` only marks the entry. HTTP stays in `trigora-client` (`import trigora_client`), which does not depend on the compiler or the CLI.
