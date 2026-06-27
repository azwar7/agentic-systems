"""
cli.py

Command-line interface for the data extractor.

Usage:
    python cli.py torvalds
    python cli.py torvalds --top 3
    python cli.py torvalds --no-cache
    python cli.py torvalds --refresh

Concepts used (Session 2):
    - argparse: positional argument, optional arguments, type conversion, defaults
    - main() + if __name__ == "__main__" + SystemExit pattern
"""

import argparse
import json
import sys

from extractor import DataExtractor, ExtractionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract a GitHub user's profile and top repositories."
    )
    parser.add_argument("username", type=str, help="GitHub username to extract data for")
    parser.add_argument(
        "--top", type=int, default=5, help="number of top repos to show (default: 5)"
    )
    parser.add_argument( #for using cache
        "--no-cache", action="store_true", help="disable reading/writing the local cache"
    )
    parser.add_argument(#for updating the cache
        "--refresh", action="store_true", help="force a fresh fetch, ignoring any existing cache"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    extractor = DataExtractor(use_cache=not args.no_cache, top_n_repos=args.top)
    print(extractor)   # uses __repr__

    try:
        data = extractor.extract(args.username, force_refresh=args.refresh)
    except ExtractionError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print(json.dumps(data, indent=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
