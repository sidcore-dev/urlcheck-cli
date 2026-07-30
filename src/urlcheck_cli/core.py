"""Core URL extraction and checking logic for urlcheck-cli.

Network access happens only through the injectable ``opener`` callable,
so unit tests can exercise the retry / error-handling logic without
making real HTTP requests.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

#: Matches http(s) URLs embedded anywhere in text, including Markdown
#: link syntax such as `[text](https://example.com)`.
URL_PATTERN = re.compile(r'https?://[^\s<>"\')\]]+')


def extract_urls(text: str) -> list[str]:
    """Extract http(s) URLs from plain text or Markdown.

    Works for a plain one-URL-per-line list as well as URLs embedded in
    Markdown prose or link syntax. Trailing punctuation commonly stuck to
    a URL in prose (periods, commas, colons, closing Markdown brackets)
    is stripped. Duplicates are removed, first-occurrence order kept.
    """
    seen: set[str] = set()
    result: list[str] = []
    for match in URL_PATTERN.findall(text):
        url = match.rstrip(".,;:!?")
        while url.endswith(")") and url.count("(") < url.count(")"):
            url = url[:-1]
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


@dataclass
class CheckResult:
    url: str
    status_code: int | None
    error: str | None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status_code is not None and self.status_code < 400


Opener = Callable[[urllib.request.Request, float], object]


def _default_opener(request: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(request, timeout=timeout)


def check_url(url: str, timeout: float = 5.0, opener: Opener = _default_opener) -> CheckResult:
    """Check a single URL with HTTP HEAD, falling back to GET if HEAD isn't allowed."""
    methods = ["HEAD", "GET"]
    for index, method in enumerate(methods):
        request = urllib.request.Request(url, method=method)
        try:
            response = opener(request, timeout)
            try:
                return CheckResult(url=url, status_code=response.getcode(), error=None)
            finally:
                close = getattr(response, "close", None)
                if close:
                    close()
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (405, 501) and index < len(methods) - 1:
                continue  # HEAD not allowed here; retry with GET
            return CheckResult(url=url, status_code=exc.code, error=None)
        except urllib.error.URLError as exc:
            return CheckResult(url=url, status_code=None, error=str(exc.reason))
        except TimeoutError:
            return CheckResult(url=url, status_code=None, error="timed out")
        except OSError as exc:
            return CheckResult(url=url, status_code=None, error=str(exc))
    return CheckResult(url=url, status_code=None, error="unknown error")


def check_urls(
    urls: list[str],
    timeout: float = 5.0,
    concurrency: int = 1,
    opener: Opener = _default_opener,
) -> list[CheckResult]:
    """Check every URL, sequentially or with a thread pool for concurrency > 1."""
    if concurrency <= 1:
        return [check_url(url, timeout, opener) for url in urls]

    results: list[CheckResult | None] = [None] * len(urls)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_index = {
            executor.submit(check_url, url, timeout, opener): i for i, url in enumerate(urls)
        }
        for future in as_completed(future_to_index):
            results[future_to_index[future]] = future.result()
    return [r for r in results if r is not None]
