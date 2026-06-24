# MicroAgent

A tiny, dependency-free Python framework that mimics the core mechanics of a
tool-calling AI agent — built specifically to practice idiomatic Python OOP
concepts (generators, decorators, context managers, descriptors, typing)
rather than to be a production agent framework.

## Why this exists

This project was built while working through Week 1 of an Agentic AI
Systems course (Python fundamentals: OOP, typing, decorators, generators,
context managers, descriptors). Instead of learning each concept in
isolation, this project combines all of them into one small, working
system that mirrors how real agent frameworks are structured internally.

## What it demonstrates

| Concept | Where it's used |
|---|---|
| `__init_subclass__` | Tools auto-register themselves into a registry on class creation (`tools.py`) |
| `Protocol` | Defines the shape every `Tool` must follow, without forcing inheritance |
| `TypedDict` | `ToolResult` — a fixed-shape dictionary for every tool's output |
| Descriptors (`__get__`/`__set__`/`__set_name__`) | `PositiveNumber` validates `rate_limit` on every tool |
| `@property` | Computed `usage_count` on each tool |
| Dunder methods | `__repr__` and `__eq__` on `BaseTool` |
| Decorators + closures + `*args`/`**kwargs` + `@wraps` | `@log_call` and `@retry(times=n)` in `decorators.py` |
| `ParamSpec` / `TypeVar` | Used to type the decorators so they preserve the wrapped function's signature |
| Generators (`yield`) | `MicroAgent.run()` streams each reasoning step lazily, one at a time |
| Context managers (class-based) | `AgentSession` opens/closes a run and prints a summary on exit |
| `enumerate` / `zip` / list comprehensions | Used in `main.py` to display tools and filter results |

## Project structure

```
microagent/
├── tools.py        # Tool protocol, base class, registry, descriptor, example tools
├── decorators.py   # @log_call and @retry(times) decorators
├── session.py      # AgentSession context manager
├── core.py         # MicroAgent — the generator-based execution loop
└── main.py         # Wires everything together and runs an example plan
```

## How it works

1. Each tool (`CalculatorTool`, `WeatherTool`, `WordCountTool`) subclasses
   `BaseTool` and supplies a `tool_name`. On class creation,
   `__init_subclass__` automatically registers it in `BaseTool.registry`.
2. `MicroAgent.run(plan)` is a generator. Given a list of
   `(tool_name, query)` steps, it yields a status string before and after
   each tool call — so output streams live instead of waiting for
   everything to finish.
3. Each tool call goes through two stacked decorators:
   - `@retry(times=2)` — retries on exception
   - `@log_call` — logs the call, arguments, duration, and result
4. `AgentSession` is a context manager wrapping the whole run. On exit it
   prints a summary: duration, total calls, successes, errors.
5. The `PositiveNumber` descriptor enforces that every tool's `rate_limit`
   is non-negative, regardless of which tool class it's attached to.

## Running it

No external dependencies — pure standard library.

```bash
python3 main.py
```

Expected output includes:
- the list of auto-registered tools
- a live stream of reasoning steps and results for a 5-step plan
  (including two intentional failure cases — an unknown city and an
  unregistered tool)
- a final session summary
- example `__repr__` output for two tools

## Extending it

Adding a new tool requires no registry editing — just subclass `BaseTool`:

```python
class TranslateTool(BaseTool, tool_name="translate"):
    def run(self, query: str) -> ToolResult:
        self._record_usage()
        return ToolResult(status="success", tool_name=self.name, output=query.upper())
```

It will automatically appear in `BaseTool.registry` and be usable in any
plan passed to `MicroAgent.run()`.

## What this is not

This is a learning project, not a production agent framework. It does not
call any real LLM API, does not make real network requests, and the
"tools" use local/fake data. It is intentionally scoped to Python language
fundamentals (OOP, typing, decorators, generators, context managers,
descriptors) rather than API integration, which is covered separately.

## Roadmap context

Built as part of Week 1 (Python for Agentic Systems) of a 16-week Agentic
AI Systems course, covering idiomatic Python, OOP, typing, and decorators
before moving on to NLP, embeddings, transformer internals, RAG, and
autonomous agent architectures in later weeks.
