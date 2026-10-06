# trigora

Python authoring SDK for Trigora durable programs. Requires CPython 3.10–3.12 until 3.13 wheels exist.

Build long-running programs that can call external systems, wait for events, sleep durably, invoke child executions, and recover from committed continuation state.

## Install

```bash
pip install trigora
```

## Quick example

```python
from trigora import effect, program, wait_for_event


@program
async def approval():
    result = await effect("generate", lambda: 42)
    review = await wait_for_event("approved")
    return {"result": result, "review": review}
```

Run it locally with:

```bash
trigora dev
trigora start approval
```

## Program entry

Trigora discovers programs from the paths configured in `trigora.toml`:

```toml
[project]
name = "my-project"
programs = ["src/**/*.py"]
```

Each matching file has one `@program` async function. That function is the program entry. The program id is the file name, so `src/approval.py` starts with `trigora start approval`.

```python
@program
async def research(topic, depth="full"):
    return {"topic": topic, "depth": depth}
```

The Python frontend implements `py.subset.v1`.

Program parameters are plain. A default must be a constant: `None`, a bool, a finite number, or a string. A missing argument uses that default. Extra arguments are rejected.

`*args`, keyword-only parameters, and positional-only parameters are not supported.

A bare `async def` is not a program entry.

## Durable primitives

- `effect(name, fn)` — run a durable external effect
- `sleep(duration)` — suspend on a durable timer
- `wait_for_event(name)` — wait for an external event
- `invoke(program, input)` — invoke a durable child execution
- `gather(*awaitables)` — wait for every durable branch
- `race(*awaitables)` — wait for the first durable branch

Effect keys and event names are string literals in the current Python subset.

## Local development

```bash
trigora init
trigora dev
trigora start approval
trigora send <execution> approved --payload '"ok"'
trigora result <execution>
```

Programs execute through the Trigora runtime rather than by running the source file directly.

## Learn more

- [Quickstart](https://trigora.dev/docs/quickstart)
- [Trigora documentation](https://trigora.dev/docs)
- [TCC Python semantics](https://github.com/trigora-dev/tcc-engine/blob/main/spec/python-subset.md)

## License

MIT © 2026 Trigora, Inc.
