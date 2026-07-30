import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from urlcheck_cli.cli import main
from urlcheck_cli.core import CheckResult


class TestCli(unittest.TestCase):
    def test_all_ok_exits_zero(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "urls.txt"
            src.write_text("https://example.com\n")
            fake_results = [CheckResult(url="https://example.com", status_code=200, error=None)]
            with patch("urlcheck_cli.cli.check_urls", return_value=fake_results) as mocked:
                out = io.StringIO()
                with redirect_stdout(out):
                    code = main([str(src)])
                mocked.assert_called_once()
            self.assertEqual(code, 0)
            self.assertIn("https://example.com -> 200 OK", out.getvalue())

    def test_failure_status_exits_one(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "urls.txt"
            src.write_text("https://example.com/missing\n")
            fake_results = [
                CheckResult(url="https://example.com/missing", status_code=404, error=None)
            ]
            with patch("urlcheck_cli.cli.check_urls", return_value=fake_results):
                out = io.StringIO()
                with redirect_stdout(out):
                    code = main([str(src)])
            self.assertEqual(code, 1)
            self.assertIn("404 FAIL", out.getvalue())

    def test_connection_error_exits_one(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "urls.txt"
            src.write_text("https://nonexistent.invalid\n")
            fake_results = [
                CheckResult(url="https://nonexistent.invalid", status_code=None, error="DNS error")
            ]
            with patch("urlcheck_cli.cli.check_urls", return_value=fake_results):
                out = io.StringIO()
                with redirect_stdout(out):
                    code = main([str(src)])
            self.assertEqual(code, 1)
            self.assertIn("ERROR: DNS error", out.getvalue())

    def test_extracts_urls_from_markdown_file(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "README.md"
            src.write_text("Check out [this link](https://example.com/page).")
            fake_results = [CheckResult(url="https://example.com/page", status_code=200, error=None)]
            with patch("urlcheck_cli.cli.check_urls", return_value=fake_results) as mocked:
                code = main([str(src)])
            called_urls = mocked.call_args[0][0]
            self.assertEqual(called_urls, ["https://example.com/page"])
            self.assertEqual(code, 0)

    def test_no_urls_found_exits_zero(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "empty.txt"
            src.write_text("no links in here")
            code = main([str(src)])
            self.assertEqual(code, 0)

    def test_missing_file_errors(self) -> None:
        code = main(["/nonexistent/file.txt"])
        self.assertEqual(code, 2)

    def test_passes_timeout_and_concurrency(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "urls.txt"
            src.write_text("https://example.com\n")
            with patch("urlcheck_cli.cli.check_urls", return_value=[]) as mocked:
                main([str(src), "--timeout", "2.5", "--concurrency", "4"])
            _, kwargs = mocked.call_args
            self.assertEqual(kwargs["timeout"], 2.5)
            self.assertEqual(kwargs["concurrency"], 4)


if __name__ == "__main__":
    unittest.main()
