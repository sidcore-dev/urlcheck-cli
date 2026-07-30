import unittest
import urllib.error

from urlcheck_cli.core import check_url, check_urls, extract_urls


class TestExtractUrls(unittest.TestCase):
    def test_plain_list_one_per_line(self) -> None:
        text = "https://example.com\nhttps://example.org\n"
        self.assertEqual(extract_urls(text), ["https://example.com", "https://example.org"])

    def test_extracts_from_markdown_link(self) -> None:
        text = "See [the docs](https://example.com/docs) for details."
        self.assertEqual(extract_urls(text), ["https://example.com/docs"])

    def test_strips_trailing_punctuation(self) -> None:
        text = "Visit https://example.com, then https://example.org."
        self.assertEqual(extract_urls(text), ["https://example.com", "https://example.org"])

    def test_deduplicates_preserving_order(self) -> None:
        text = "https://example.com\nhttps://example.org\nhttps://example.com\n"
        self.assertEqual(extract_urls(text), ["https://example.com", "https://example.org"])

    def test_no_urls_returns_empty_list(self) -> None:
        self.assertEqual(extract_urls("just some plain text, no links here"), [])

    def test_handles_bare_markdown_url_in_parens(self) -> None:
        text = "(https://example.com)"
        self.assertEqual(extract_urls(text), ["https://example.com"])


class _FakeResponse:
    def __init__(self, code: int) -> None:
        self._code = code
        self.closed = False

    def getcode(self) -> int:
        return self._code

    def close(self) -> None:
        self.closed = True


class TestCheckUrl(unittest.TestCase):
    def test_success_on_head(self) -> None:
        def opener(request, timeout):
            self.assertEqual(request.get_method(), "HEAD")
            return _FakeResponse(200)

        result = check_url("https://example.com", opener=opener)
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.error)
        self.assertTrue(result.ok)

    def test_falls_back_to_get_when_head_not_allowed(self) -> None:
        calls = []

        def opener(request, timeout):
            calls.append(request.get_method())
            if request.get_method() == "HEAD":
                raise urllib.error.HTTPError(request.full_url, 405, "Method Not Allowed", {}, None)
            return _FakeResponse(200)

        result = check_url("https://example.com", opener=opener)
        self.assertEqual(calls, ["HEAD", "GET"])
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.ok)

    def test_4xx_status_is_not_ok(self) -> None:
        def opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

        result = check_url("https://example.com/missing", opener=opener)
        self.assertEqual(result.status_code, 404)
        self.assertFalse(result.ok)

    def test_connection_error_reports_reason(self) -> None:
        def opener(request, timeout):
            raise urllib.error.URLError("Name or service not known")

        result = check_url("https://nonexistent.invalid", opener=opener)
        self.assertIsNone(result.status_code)
        self.assertIn("Name or service not known", result.error)
        self.assertFalse(result.ok)

    def test_timeout_reports_error(self) -> None:
        def opener(request, timeout):
            raise TimeoutError()

        result = check_url("https://example.com", opener=opener)
        self.assertIsNone(result.status_code)
        self.assertEqual(result.error, "timed out")
        self.assertFalse(result.ok)


class TestCheckUrls(unittest.TestCase):
    def test_sequential_checks_all_urls(self) -> None:
        def opener(request, timeout):
            return _FakeResponse(200)

        results = check_urls(["https://a.example", "https://b.example"], opener=opener)
        self.assertEqual([r.url for r in results], ["https://a.example", "https://b.example"])
        self.assertTrue(all(r.ok for r in results))

    def test_concurrent_checks_all_urls_in_order(self) -> None:
        def opener(request, timeout):
            return _FakeResponse(200)

        urls = [f"https://{i}.example" for i in range(5)]
        results = check_urls(urls, concurrency=3, opener=opener)
        self.assertEqual([r.url for r in results], urls)
        self.assertTrue(all(r.ok for r in results))


if __name__ == "__main__":
    unittest.main()
