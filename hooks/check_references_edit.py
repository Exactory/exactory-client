#!/usr/bin/env python3
"""PostToolUse advisory: offline sanity checks on an edited references file.

Acts only when the edited file ends in `.bib` and lives inside a draft workspace
(an ancestor directory holds `.exactory/draft.json`). It runs offline-only checks —
the file parses as BibTeX (the same tolerant grammar `exactory-check` uses, inlined
here so the hook stays standalone), no duplicate keys, every entry carries a DOI or
an arXiv id — and returns findings as `additionalContext`. It never touches the
network. Any other file, a clean file, and any internal error are all silent:
exit 0, no output.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_MAX_SHOWN_FINDINGS = 4
_FIELD_NAME_RE = re.compile(r"([A-Za-z][A-Za-z0-9_\-]*)\s*=\s*")
_ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?\b")


def _read_delimited(text: str, start: int, open_char: str, close_char: str) -> tuple[str, int]:
    """Read a brace-balanced (or quote-terminated) value whose opening delimiter is at
    ``start``. Return (inner_text, index_after_close)."""
    length = len(text)
    if open_char == '"':  # quoted value: read to the next '"' that is not inside braces
        index = start + 1
        pieces = []
        brace_depth = 0
        while index < length:
            char = text[index]
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth = max(0, brace_depth - 1)
            elif char == '"' and brace_depth == 0:
                return "".join(pieces), index + 1
            pieces.append(char)
            index += 1
        return "".join(pieces), index
    depth = 0
    index = start
    while index < length:
        char = text[index]
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
        index += 1
    return text[start + 1 :], length


def _clean(value: str) -> str:
    """Strip LaTeX braces and collapse whitespace so field values compare cleanly."""
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip().strip(",").strip()


def _parse_fields(body: str) -> dict:
    fields: dict[str, str] = {}
    index, length = 0, len(body)
    while index < length:
        while index < length and body[index] in " \t\r\n,":
            index += 1
        match = _FIELD_NAME_RE.match(body[index:])
        if not match:
            break
        field_name = match.group(1).lower()
        index += match.end()
        if index >= length:
            break
        char = body[index]
        if char == "{":
            value, index = _read_delimited(body, index, "{", "}")
        elif char == '"':
            value, index = _read_delimited(body, index, '"', '"')
        else:  # bare value (a number or an abbreviation macro) up to the next comma
            end = index
            while end < length and body[end] != ",":
                end += 1
            value, index = body[index:end], end
        fields[field_name] = _clean(value)
    return fields


def _parse_bib(text: str) -> list[dict]:
    """Tolerant BibTeX parser. Return a list of {type, key, ...fields}. Skips
    ``@comment``/``@string``/``@preamble`` blocks and bodies with no comma (an
    entry with a key but no fields); a keyless entry is kept with an empty key."""
    entries: list[dict] = []
    index, length = 0, len(text)
    while True:
        at = text.find("@", index)
        if at == -1:
            break
        end = at + 1
        while end < length and text[end].isalpha():
            end += 1
        entry_type = text[at + 1 : end].lower()
        while end < length and text[end] not in "{(":
            end += 1
        if end >= length:
            break
        if text[end] == "{":
            body, index = _read_delimited(text, end, "{", "}")
        else:
            body, index = _read_delimited(text, end, "(", ")")
        if entry_type in ("comment", "string", "preamble"):
            continue
        if "," not in body:
            continue
        key, rest = body.split(",", 1)
        entry = {"type": entry_type, "key": key.strip()}
        entry.update(_parse_fields(rest))
        entries.append(entry)
    return entries


def _has_registry_id(entry: dict) -> bool:
    if entry.get("doi") or entry.get("eprint"):
        return True
    haystack = " ".join(entry.get(field, "") for field in ("url", "note", "howpublished", "journal"))
    return "arxiv" in haystack.lower() and _ARXIV_ID_RE.search(haystack) is not None


def _collect_findings(bib_text: str) -> list[str]:
    entries = _parse_bib(bib_text)
    if not entries:
        return ["the file has no BibTeX entry that parses"] if bib_text.strip() else []
    findings: list[str] = []
    key_counts: dict[str, int] = {}
    for entry in entries:
        key_counts[entry["key"]] = key_counts.get(entry["key"], 0) + 1
    findings.extend(
        f"duplicate key: {key} appears {count} times"
        for key, count in key_counts.items()
        if key and count > 1
    )
    findings.extend(
        f"entry {entry['key'] or '(no key)'} has no DOI and no arXiv id"
        for entry in entries
        if not _has_registry_id(entry)
    )
    return findings


def main() -> None:
    payload = json.load(sys.stdin)
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path.endswith(".bib"):
        sys.exit(0)

    bib_path = Path(file_path)
    if not bib_path.is_absolute():
        bib_path = Path(payload.get("cwd") or ".") / bib_path
    bib_path = bib_path.resolve()
    is_in_workspace = any(
        (directory / ".exactory" / "draft.json").is_file() for directory in bib_path.parents
    )
    if not is_in_workspace:
        sys.exit(0)

    findings = _collect_findings(bib_path.read_text(encoding="utf-8", errors="replace"))
    if not findings:
        sys.exit(0)

    shown_findings = findings
    if len(findings) > _MAX_SHOWN_FINDINGS:
        hidden_count = len(findings) - (_MAX_SHOWN_FINDINGS - 1)
        shown_findings = findings[: _MAX_SHOWN_FINDINGS - 1] + [f"and {hidden_count} more"]
    context_lines = [f"Offline check of {bib_path.name} found {len(findings)} problem(s):"]
    context_lines.extend("- " + finding for finding in shown_findings)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n".join(context_lines),
                }
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
