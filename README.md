<p align="center">
  <a href="https://trigora.dev">
    <img src="https://trigora.dev/py-banner.png" alt="Trigora / Python — durable execution without history replay." width="100%" />
  </a>
</p>

# Trigora for Python

**Durable execution for Python without history replay.**

Build long-lived agents and programs that survive waits, external effects, events, and process failure.

Trigora uses **Transparent Continuation Checkpointing (TCC)** to resume from committed continuation state rather than replaying completed execution history.

Requires Python 3.10+.

## Install

```sh
pip install trigora trigora-client trigora-cli
```

- `trigora` — Python authoring package
- `trigora-client` — Trigora Cloud API client
- `trigora-cli` — `trigora` command-line interface

## Quickstart

Initialize a project:

```sh
trigora init
```

Run locally:

```sh
trigora dev
```

Deploy:

```sh
trigora deploy
```

See the [quickstart](https://trigora.dev/docs/quickstart).

## Durable programs

Trigora programs can:

- run external effects;
- wait for events;
- sleep durably;
- invoke child executions;
- use structured concurrency;
- recover after worker or process failure.

The Python frontend implements a declared language subset. See the [TCC Python semantics](https://github.com/trigora-dev/tcc-engine/blob/main/spec/python-subset.md).

## Packages

### `trigora`

Authoring surface for durable Python programs.

### `trigora-client`

Python client for the Trigora Cloud API.

### `trigora-cli`

Native Trigora CLI distributed through PyPI.

## Ecosystem

- [Trigora](https://github.com/trigora-dev/trigora)
- [Trigora for TypeScript](https://github.com/trigora-dev/trigora-typescript)
- [Trigora for Rust](https://github.com/trigora-dev/trigora-rust)
- [TCC Engine](https://github.com/trigora-dev/tcc-engine)

## Links

- [Website](https://trigora.dev)
- [Documentation](https://trigora.dev/docs)
- [Trigora Cloud](https://cloud.trigora.dev)
- [Research](https://trigora.dev/research)
- [Technical report](https://trigora.dev/research/whitepaper)

## License

MIT © 2026 Trigora, Inc.
