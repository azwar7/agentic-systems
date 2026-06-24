"""
decorators.py

Defines:
- log_call  -> logs before/after every tool call, with timing
- retry     -> decorator factory, retries a function N times on failure
"""

import time
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def log_call(func: Callable[P, R]) -> Callable[P, R]:
    """Logs the function name, arguments, duration, and result."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        tool_self = args[0] if args else None
        tool_label = getattr(tool_self, "name", func.__name__)

        print(f"[LOG] -> calling '{tool_label}' with args={args[1:]} kwargs={kwargs}")
        start = time.time()

        result = func(*args, **kwargs)

        elapsed = time.time() - start
        print(f"[LOG] <- '{tool_label}' finished in {elapsed:.4f}s -> {result}")
        return result

    return wrapper


def retry(times: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator factory: retries the wrapped function up to `times` times."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    last_error = error
                    print(f"[RETRY] attempt {attempt}/{times} failed: {error}")
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator
