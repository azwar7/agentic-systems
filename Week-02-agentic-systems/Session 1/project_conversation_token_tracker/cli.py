"""
cli.py

Command-line interface for the conversation cost tracker.

Reads a conversation from a JSON file shaped like:
    [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        ...
    ]

Usage:
    python cli.py conversation.json
    python cli.py conversation.json --bpe
    python cli.py conversation.json --price-per-token 0.000003
    python cli.py conversation.json --output-price-per-token 0.000015
    python cli.py conversation.json --context-limit 200000
"""

import argparse
import json
import sys

from tracker import ConversationCostTracker, Message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Track cumulative token cost across a simulated conversation."
    )
    parser.add_argument("file", type=str, help="path to a JSON file containing the conversation")
    parser.add_argument(
        "--bpe",
        action="store_true",
        help="use real BPE token counts (tiktoken) instead of the len//4 approximation",
    )
    parser.add_argument(
        "--price-per-token",
        type=float,
        default=3.00 / 1_000_000,
        help="input price per token in USD (default: Claude Sonnet-ish rate)",
    )
    parser.add_argument(
        "--output-price-per-token",
        type=float,
        default=15.00 / 1_000_000,
        help="output price per token in USD (default: Claude Sonnet-ish rate)",
    )
    parser.add_argument(
        "--context-limit", type=int, default=200_000, help="context window size in tokens"
    )
    return parser


def load_conversation(path: str) -> list[Message]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages: list[Message] = []
    for item in data:
        if "role" not in item or "content" not in item:
            raise ValueError(f"each message needs 'role' and 'content', got: {item}")
        messages.append(Message(role=item["role"], content=item["content"]))
    return messages


def print_report(tracker: ConversationCostTracker) -> None:
    print(f"{'Turn':<6}{'Role':<12}{'New tok':<10}{'Cumulative tok':<16}{'Cumulative cost':<18}Note")
    print("-" * 100)

    for turn in tracker.cost_per_turn():
        tokens_label = f"{turn['new_tokens']}" + ("" if turn["exact"] else "~")
        print(
            f"{turn['turn']:<6}{turn['role']:<12}{tokens_label:<10}"
            f"{turn['cumulative_tokens']:<16}${turn['cumulative_cost']:<17.6f}{turn['note']}"
        )

    print()
    print(f"Total tokens so far : {tracker.total_tokens_so_far()}")
    print(f"Total cost so far   : ${tracker.total_cost_so_far():.6f}")
    print(f"Context window used : {tracker.context_usage_percent():.4f}%")
    print(f"Tokenizer used      : {'real BPE (tiktoken)' if tracker.use_bpe else 'approximate (len // 4)'}")

    if tracker.is_near_context_limit():
        print("[WARNING] conversation is approaching the context window limit")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        messages = load_conversation(args.file)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    tracker = ConversationCostTracker(
        input_price_per_token=args.price_per_token,
        output_price_per_token=args.output_price_per_token,
        context_window_limit=args.context_limit,
        use_bpe=args.bpe,
    )
    tracker.messages = messages

    print(tracker)
    print()
    print_report(tracker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
