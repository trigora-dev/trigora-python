from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def _require_runtime() -> None:
    raise RuntimeError(
        "Durable primitives can only run inside a Trigora execution. Start the program with the Trigora client while `trigora dev` is running."
    )


def program(fn: T) -> T:
    return fn


def effect(name: str, fn: Callable[[], T]) -> T:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("effect(name, fn) requires a non-empty string key.")
    if not callable(fn):
        raise TypeError("effect(name, fn) requires a function.")
    _require_runtime()


def wait_for_event(name: str) -> object:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("wait_for_event(name) requires a non-empty string.")
    _require_runtime()


def sleep(duration: float | str) -> None:
    del duration
    _require_runtime()


def invoke(name: str, input: object | None = None) -> object:
    del input
    if not isinstance(name, str) or not name.strip():
        raise ValueError("invoke(name, input) requires a non-empty program name.")
    _require_runtime()


def gather(*awaitables: object) -> object:
    if not awaitables:
        raise ValueError("gather() requires at least one awaitable.")
    _require_runtime()


def race(*awaitables: object) -> object:
    if not awaitables:
        raise ValueError("race() requires at least one awaitable.")
    _require_runtime()
