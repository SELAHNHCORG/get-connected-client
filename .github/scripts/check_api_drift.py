#!/usr/bin/env python3
"""Detect drift between Galaxy Digital's published OpenAPI spec and our copy.

``doc/api.yml`` is the vendored source of truth for this client -- the test
suite asserts 100% path coverage against it. Galaxy Digital publishes the
authoritative spec at https://api.galaxydigital.com/docs/ (a public Swagger UI
page, no credentials involved). This script fetches that spec and compares it
to the vendored file so a weekly GitHub Action can open an issue when upstream
moves.

Exit codes:

* ``0`` -- the specs are byte-identical (no drift)
* ``1`` -- drift detected; a markdown report was written
* ``2`` -- the spec could not be fetched or parsed

Everything fetched from the network is treated as untrusted text: it is never
evaluated, only diffed, and it is embedded in the report inside fenced code
blocks whose fence is widened past any backtick run in the content.

Run it with::

    uv run --no-project --with pyyaml --with httpx \\
        python .github/scripts/check_api_drift.py --output drift.md
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import yaml

DOCS_URL = "https://api.galaxydigital.com/docs/"
FALLBACK_SPEC = "api.yml"
DEFAULT_VENDORED = Path(__file__).resolve().parents[2] / "doc" / "api.yml"
DIFF_LIMIT = 400
TIMEOUT = 60.0

EXIT_NO_DRIFT = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2

# The swagger bootstrap embeds the spec location as ``url: "api.yml?v=1.9.2"``.
SPEC_URL_RE = re.compile(r"""url\s*:\s*["']([^"'\s]+\.ya?ml(?:\?[^"'\s]*)?)["']""")

HTTP_METHODS = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)


class DriftCheckError(RuntimeError):
    """Raised when the live spec cannot be retrieved or understood."""


def fetch_text(client: httpx.Client, url: str, what: str) -> str:
    """GET ``url`` and return its body as text, or raise DriftCheckError."""
    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise DriftCheckError(
            f"failed to fetch {what} from {url}: HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise DriftCheckError(f"failed to fetch {what} from {url}: {exc}") from exc
    return response.text


def discover_spec_url(client: httpx.Client, docs_url: str) -> str:
    """Resolve the live spec URL from the swagger page, falling back to api.yml.

    The extracted value is untrusted, so the resolved URL is required to stay on
    the docs host -- a rewritten page cannot point us at some other server.
    """
    fallback = urljoin(docs_url, FALLBACK_SPEC)
    try:
        html = fetch_text(client, docs_url, "the API docs page")
    except DriftCheckError as exc:
        print(f"warning: {exc}; falling back to {fallback}", file=sys.stderr)
        return fallback

    match = SPEC_URL_RE.search(html)
    if not match:
        print(
            f"warning: no spec url found in {docs_url}; falling back to {fallback}",
            file=sys.stderr,
        )
        return fallback

    candidate = urljoin(docs_url, match.group(1))
    if urlparse(candidate).netloc != urlparse(docs_url).netloc:
        print(
            f"warning: discovered spec url {candidate} is off-host; "
            f"falling back to {fallback}",
            file=sys.stderr,
        )
        return fallback
    return candidate


def parse_spec(text: str, label: str) -> dict[str, Any]:
    """Parse an OpenAPI document with the safe loader."""
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DriftCheckError(
            f"could not parse the {label} spec as YAML: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise DriftCheckError(
            f"the {label} spec is not a YAML mapping (got {type(parsed).__name__})"
        )
    return parsed


def spec_version(spec: dict[str, Any]) -> str:
    """Best-effort ``info.version`` lookup."""
    info = spec.get("info")
    if isinstance(info, dict) and info.get("version") is not None:
        return str(info["version"])
    return "unknown"


def spec_paths(spec: dict[str, Any]) -> dict[str, Any]:
    paths = spec.get("paths")
    return paths if isinstance(paths, dict) else {}


def _methods(item: Any) -> set[str]:
    if not isinstance(item, dict):
        return set()
    return {key for key in item if isinstance(key, str) and key.lower() in HTTP_METHODS}


def describe_path_change(live_item: Any, vendored_item: Any) -> str | None:
    """Summarize how one path item changed, or None when it is unchanged."""
    if live_item == vendored_item:
        return None

    live_methods, vendored_methods = _methods(live_item), _methods(vendored_item)
    notes: list[str] = []
    if added := sorted(m.upper() for m in live_methods - vendored_methods):
        notes.append(f"operations added: {', '.join(added)}")
    if removed := sorted(m.upper() for m in vendored_methods - live_methods):
        notes.append(f"operations removed: {', '.join(removed)}")

    if isinstance(live_item, dict) and isinstance(vendored_item, dict):
        changed = sorted(
            method.upper()
            for method in live_methods & vendored_methods
            if live_item[method] != vendored_item[method]
        )
        if changed:
            notes.append(f"operations changed: {', '.join(changed)}")
        live_other = {k: v for k, v in live_item.items() if k not in live_methods}
        vendored_other = {
            k: v for k, v in vendored_item.items() if k not in vendored_methods
        }
        if live_other != vendored_other:
            notes.append("path-level metadata changed")

    return "; ".join(notes) if notes else "contents changed"


def fence_for(content: str) -> str:
    """A code fence long enough that ``content`` cannot break out of it."""
    longest = max((len(run) for run in re.findall(r"`+", content)), default=0)
    return "`" * max(3, longest + 1)


def render_report(
    *,
    live_text: str,
    vendored_text: str,
    live_spec: dict[str, Any],
    vendored_spec: dict[str, Any],
    spec_url: str,
    vendored_path: Path,
    diff_limit: int,
) -> str:
    live_paths = spec_paths(live_spec)
    vendored_paths = spec_paths(vendored_spec)

    added = sorted(set(live_paths) - set(vendored_paths))
    removed = sorted(set(vendored_paths) - set(live_paths))
    changed = [
        (path, note)
        for path in sorted(set(live_paths) & set(vendored_paths))
        if (note := describe_path_change(live_paths[path], vendored_paths[path]))
    ]

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    live_row = (
        f"| live | `{spec_version(live_spec)}` | {len(live_paths)} "
        f"| {len(live_text.encode())} |"
    )
    vendored_row = (
        f"| vendored | `{spec_version(vendored_spec)}` | {len(vendored_paths)} "
        f"| {len(vendored_text.encode())} |"
    )

    lines = [
        "## Upstream API spec drift",
        "",
        f"The live Get Connected OpenAPI spec no longer matches `{vendored_path}`.",
        "",
        "| | version | paths | bytes |",
        "| --- | --- | --- | --- |",
        live_row,
        vendored_row,
        "",
        f"Live spec fetched from <{spec_url}> at {fetched_at}.",
        "",
        "### Paths",
        "",
    ]

    if not (added or removed or changed):
        lines += [
            (
                "No path-level differences -- the drift is confined to other "
                "parts of the document (see the diff below)."
            ),
            "",
        ]
    else:
        for title, entries in (
            ("Added", [(path, None) for path in added]),
            ("Removed", [(path, None) for path in removed]),
            ("Changed", changed),
        ):
            if not entries:
                continue
            lines += [f"**{title} ({len(entries)})**", ""]
            for path, note in entries:
                suffix = f" -- {note}" if note else ""
                lines.append(f"- `{path}`{suffix}")
            lines.append("")

    diff = list(
        difflib.unified_diff(
            vendored_text.splitlines(),
            live_text.splitlines(),
            fromfile=f"vendored/{vendored_path.name}",
            tofile="live/api.yml",
            lineterm="",
        )
    )
    truncated = len(diff) > diff_limit
    shown = diff[:diff_limit] if truncated else diff
    summary = (
        f"Unified diff (first {diff_limit} of {len(diff)} lines)"
        if truncated
        else f"Unified diff ({len(diff)} lines)"
    )
    body = "\n".join(shown)
    fence = fence_for(body)

    lines += [
        "### Diff",
        "",
        "<details>",
        f"<summary>{summary}</summary>",
        "",
        f"{fence}diff",
        body,
        fence,
        "",
    ]
    if truncated:
        lines.append(
            f"_Diff truncated at {diff_limit} lines; "
            f"{len(diff) - diff_limit} more lines were omitted._"
        )
        lines.append("")
    lines += [
        "</details>",
        "",
        (
            "Refresh the vendored copy with the live spec once the change has "
            "been reviewed, then update the client and its tests to match."
        ),
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Galaxy Digital's published OpenAPI spec with the vendored copy."
        )
    )
    parser.add_argument(
        "--docs-url",
        default=DOCS_URL,
        help=f"Swagger UI page used to discover the spec URL (default: {DOCS_URL})",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Fetch the live spec from this URL instead of discovering it.",
    )
    parser.add_argument(
        "--vendored",
        type=Path,
        default=DEFAULT_VENDORED,
        help=f"Vendored spec to compare against (default: {DEFAULT_VENDORED})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the drift report here (default: stdout).",
    )
    parser.add_argument(
        "--save-live",
        type=Path,
        default=None,
        help="Write the fetched live spec here.",
    )
    parser.add_argument(
        "--diff-limit",
        type=int,
        default=DIFF_LIMIT,
        help=f"Maximum diff lines to embed in the report (default: {DIFF_LIMIT})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        vendored_text = args.vendored.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: could not read vendored spec: {exc}", file=sys.stderr)
        return EXIT_ERROR

    try:
        with httpx.Client(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "get-connected-client-drift-check"},
        ) as client:
            spec_url = args.url or discover_spec_url(client, args.docs_url)
            live_text = fetch_text(client, spec_url, "the live API spec")
    except DriftCheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.save_live:
        args.save_live.write_text(live_text, encoding="utf-8")

    if live_text == vendored_text:
        print(f"no drift: {spec_url} matches {args.vendored}")
        return EXIT_NO_DRIFT

    try:
        live_spec = parse_spec(live_text, "live")
        vendored_spec = parse_spec(vendored_text, "vendored")
    except DriftCheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    report = render_report(
        live_text=live_text,
        vendored_text=vendored_text,
        live_spec=live_spec,
        vendored_spec=vendored_spec,
        spec_url=spec_url,
        vendored_path=args.vendored,
        diff_limit=args.diff_limit,
    )

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"drift detected: report written to {args.output}", file=sys.stderr)
    else:
        print(report)
    return EXIT_DRIFT


if __name__ == "__main__":
    raise SystemExit(main())
