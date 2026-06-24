"""
main.py

Wires everything together:
- opens an AgentSession (context manager)
- creates a MicroAgent
- runs a plan through the generator, printing each step as it streams
- the registered tools are listed using zip/enumerate for variety
"""

from core import MicroAgent
from session import AgentSession
from tools import BaseTool, CalculatorTool, WeatherTool, WordCountTool  # noqa: F401 (registers tools)


def show_registered_tools() -> None:
    print("Registered tools:")
    names = list(BaseTool.registry.keys())
    classes = list(BaseTool.registry.values())
    for i, (name, cls) in enumerate(zip(names, classes), start=1):
        print(f"  {i}. {name} -> {cls.__name__}")
    print()


def main() -> None:
    show_registered_tools()

    plan = [
        ("calculator", "5 * (3 + 2)"),
        ("weather", "Islamabad"),
        ("word_count", "the quick brown fox jumps over the lazy dog"),
        ("weather", "Tokyo"),          # will produce an error result
        ("unknown_tool", "test"),      # tool not in registry
    ]

    with AgentSession() as session: #this runs --> def __enter__(self) -> "AgentSession":
        agent = MicroAgent(session=session)
        #session is the object
        for step_output in agent.run(plan):
            print(step_output)

    print("\nFinal tool object reprs (dunder __repr__ in action):")
    for tool_name in ["calculator", "weather"]:
        tool = BaseTool.registry[tool_name]()
        print(f"  {tool!r}")


if __name__ == "__main__":
    main()
