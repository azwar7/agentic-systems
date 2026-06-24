"""
core.py

Defines:
- MicroAgent -> a tiny "agent" that takes a list of (tool_name, query) steps
  and runs them one at a time, yielding each step's result live (generator).
"""

from decorators import log_call, retry
from tools import BaseTool, ToolResult
from session import AgentSession
from typing import Generator


class MicroAgent:
    def __init__(self, session: AgentSession | None = None) -> None:
        self.session = session

    @log_call
    @retry(times=2)
    def _execute_tool(self, tool_name: str, query: str) -> ToolResult:
        if tool_name not in BaseTool.registry:
            return ToolResult(
                status="error", tool_name=tool_name, output=f"unknown tool '{tool_name}'"
            )
        tool_cls = BaseTool.registry[tool_name]
        tool = tool_cls()
        return tool.run(query)

    def run(self, plan: list[tuple[str, str]]) -> Generator[str, None, None]:
        """
        Takes a plan: list of (tool_name, query) pairs.
        Yields a human-readable string for each step, one at a time (lazy).
        """
        for index, (tool_name, query) in enumerate(plan, start=1):
            yield f"Step {index}: thinking about calling '{tool_name}' with '{query}'"

            result = self._execute_tool(tool_name, query)

            if self.session is not None:
                self.session.record(result)

            yield f"Step {index} result -> [{result['status']}] {result['output']}"
