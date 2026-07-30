# urlcheck-cli

A small, dependency-free command-line tool that checks a list of URLs —
or URLs embedded in a Markdown file — and reports the HTTP status code
or error for each.

## Why

Link rot is quiet: a README full of dead links, or a scraped list of
URLs with a few that no longer resolve, looks fine until someone clicks.
`urlcheck-cli` checks them all in one pass using only the Python
standard library, so it's easy to drop into a CI job or pre-commit hook
without pulling in a dependency like `requests`.

## Install

```bash
pip install .
```

This installs a `urlcheck-cli` command on your PATH.

## Usage

```bash
urlcheck-cli urls.txt
```

`urls.txt` can be a plain one-URL-per-line list, or any text file (a
Markdown README, for example) with `http(s)://` URLs embedded in it —
including inside Markdown link syntax like `[text](https://example.com)`.
URLs are extracted, deduplicated, and checked with an HTTP HEAD request,
falling back to GET if the server rejects HEAD (405/501).

Example output:

```
https://example.com -> 200 OK
https://example.com/docs -> 200 OK
https://example.com/missing -> 404 FAIL
https://nonexistent.invalid -> ERROR: [Errno 8] nodename nor servname provided, or not known
```

Reads from a file argument or stdin, so it doubles as a README link
checker:

```bash
urlcheck-cli README.md
cat urls.txt | urlcheck-cli --timeout 10 --concurrency 8
```

### Options

| Flag            | Description                                               |
|-----------------|-------------------------------------------------------------|
| `file`          | Input file to read (default: stdin)                         |
| `--timeout`     | Request timeout in seconds (default: 5)                     |
| `--concurrency` | Number of URLs to check in parallel (default: 1, sequential)|

### Exit codes

- `0` — every URL returned a successful (< 400) status
- `1` — at least one URL failed to connect, timed out, or returned a 4xx/5xx status
- `2` — the input file couldn't be read

## Development

```bash
pip install -e .
python -m unittest discover -s tests -v
```

## License

All rights reserved. This code is public for viewing and reference only —
no license is granted to use, copy, modify, or redistribute it. See
[LICENSE](LICENSE) for details.
