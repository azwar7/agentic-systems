"""
session.py

Defines:
- AgentSession -> class-based context manager.
  Opens a "session" before the agent runs, and on exit prints
  a summary: total duration, total tool calls, success/error counts.
"""

import time
from tools import BaseTool


class AgentSession:
    def __init__(self) -> None:
        self._start_time: float = 0.0
        self.tool_calls: list[dict] = []

    def __enter__(self) -> "AgentSession":
        self._start_time = time.time()
        print("[SESSION] agent session started")
        return self

    def record(self, result: dict) -> None:
        self.tool_calls.append(result)

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        elapsed = time.time() - self._start_time

        successes = [r for r in self.tool_calls if r["status"] == "success"]
        errors = [r for r in self.tool_calls if r["status"] == "error"]

        print("\n[SESSION] ---- summary ----")
        print(f"[SESSION] duration       : {elapsed:.4f}s")
        print(f"[SESSION] total tool calls: {len(self.tool_calls)}")
        print(f"[SESSION] successes       : {len(successes)}")
        print(f"[SESSION] errors          : {len(errors)}")
        print(f"[SESSION] registered tools: {len(BaseTool.registry)}")

        if exc_type is not None:
            print(f"[SESSION] session ended due to exception: {exc_type.__name__}: {exc_val}")
            return False   # don't suppress the exception

        print("[SESSION] agent session ended cleanly")
        return False
