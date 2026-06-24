"""
tools.py

Defines:
- ToolResult (TypedDict)  -> shape of every tool's output
- Tool (Protocol)         -> what every tool must implement
- PositiveNumber          -> a descriptor used to validate rate_limit
- BaseTool                -> base class using __init_subclass__ to auto-register tools
"""

from typing import Protocol, TypedDict, Literal


# ---------------------------------------------------------------------------
# TypedDict — fixed shape for every tool's result
# ---------------------------------------------------------------------------
class ToolResult(TypedDict):
    status: Literal["success", "error"]
    tool_name: str
    output: str


# ---------------------------------------------------------------------------
# Protocol — defines the SHAPE a tool must have (no inheritance forced)
# ---------------------------------------------------------------------------
class Tool(Protocol):
    name: str

    def run(self, query: str) -> ToolResult: ...


# ---------------------------------------------------------------------------
# Descriptor — validates rate_limit is always positive, reusable on any class
# ---------------------------------------------------------------------------
class PositiveNumber:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if value < 0:
            raise ValueError(f"{self.name} must be positive")
        obj.__dict__[self.name] = value


# ---------------------------------------------------------------------------
# BaseTool — uses __init_subclass__ to auto-register every tool subclass
# ---------------------------------------------------------------------------
class BaseTool:
    registry: dict[str, type["BaseTool"]] = {}

    # descriptor plugged in — every tool gets a validated rate_limit
    rate_limit = PositiveNumber()

    def __init_subclass__(cls, tool_name: str | None = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if tool_name is None:
            raise TypeError(f"{cls.__name__} must define tool_name")
        BaseTool.registry[tool_name] = cls
        cls.name = tool_name

    def __init__(self, rate_limit: int = 100) -> None:
        self.rate_limit = rate_limit   # triggers descriptor __set__
        self._usage_count = 0

    # ---- dunder methods ----
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, calls={self._usage_count})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, BaseTool):
            return False
        return self.name == other.name

    # ---- computed property ----
    @property
    def usage_count(self) -> int:
        return self._usage_count

    def _record_usage(self) -> None:
        self._usage_count += 1

    def run(self, query: str) -> ToolResult:
        raise NotImplementedError("Subclasses must implement run()")


# ---------------------------------------------------------------------------
# Concrete tools — each one registers itself automatically
# ---------------------------------------------------------------------------
class CalculatorTool(BaseTool, tool_name="calculator"):
    def run(self, query: str) -> ToolResult:
        self._record_usage()
        try:
            result = eval(query, {"__builtins__": {}})
            return ToolResult(status="success", tool_name=self.name, output=str(result))
        except Exception as e:
            return ToolResult(status="error", tool_name=self.name, output=str(e))


class WeatherTool(BaseTool, tool_name="weather"):
    _fake_db = {
        "islamabad": "32C, sunny",
        "london": "18C, cloudy",
        "karachi": "35C, humid",
    }

    def run(self, query: str) -> ToolResult:
        self._record_usage()
        city_key = query.strip().lower()
        if city_key in self._fake_db:
            return ToolResult(
                status="success",
                tool_name=self.name,
                output=f"{query}: {self._fake_db[city_key]}",
            )
        return ToolResult(
            status="error", tool_name=self.name, output=f"no weather data for '{query}'"
        )


class WordCountTool(BaseTool, tool_name="word_count"):
    def run(self, query: str) -> ToolResult:
        self._record_usage()
        words = query.split()
        return ToolResult(
            status="success", tool_name=self.name, output=f"{len(words)} words"
        )
