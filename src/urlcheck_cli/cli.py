"""Command-line entry point for urlcheck-cli."""
from __future__ import annotations

import argparse
import sys

from .core import CheckResult, check_urls, extract_urls


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="urlcheck-cli",
        description="Check a list of URLs (or URLs embedded in a Markdown file) with HTTP "
        "HEAD, falling back to GET, and report status codes or errors.",
    )
    parser.add_argument(
        "file", nargs="?", default=None, help="Input file to read (default: stdin)"
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds (default: 5)")
    parser.add_argument(
        "--concurrency", type=int, default=1, help="Number of URLs to check in parallel (default: 1, sequential)"
    )
    return parser


def _read_input(path: str | None) -> str:
    if path is None:
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _format_result(result: CheckResult) -> str:
    if result.error is not None:
        return f"{result.url} -> ERROR: {result.error}"
    marker = "OK" if result.ok else "FAIL"
    return f"{result.url} -> {result.status_code} {marker}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.file)
    except OSError as exc:
        print(f"urlcheck-cli: error: could not read input: {exc}", file=sys.stderr)
        return 2

    urls = extract_urls(text)
    if not urls:
        print("urlcheck-cli: no URLs found in input", file=sys.stderr)
        return 0

    results = check_urls(urls, timeout=args.timeout, concurrency=args.concurrency)

    any_failed = False
    for result in results:
        print(_format_result(result))
        if not result.ok:
            any_failed = True

    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
