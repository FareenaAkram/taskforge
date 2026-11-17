"""Tiny, dependency-free unified-diff creation and application (no `patch`/`git` needed)."""

from __future__ import annotations

import difflib
import re

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(ValueError):
    """Raised when a patch does not apply cleanly."""


def make_patch(old: str, new: str, path: str) -> str:
    """Unified diff turning `old` into `new` for a file called `path`."""
    return "".join(
        difflib.unified_diff(
            old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}", n=3
        )
    )


def apply_patch(source: str, patch: str) -> str:
    """Apply a single-file unified diff to `source`, verifying every context line."""
    src = source.splitlines(True)
    lines = patch.splitlines(True)
    out: list[str] = []
    pos = 0
    i = 0
    while i < len(lines) and not lines[i].startswith("@@"):
        i += 1
    while i < len(lines):
        m = _HUNK.match(lines[i])
        if not m:
            raise PatchError(f"bad hunk header: {lines[i]!r}")
        start = int(m.group(1)) - 1
        if m.group(2) == "0":
            start += 1
        if start < pos:
            raise PatchError("overlapping hunks")
        out.extend(src[pos:start])
        pos = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@"):
            tag, body = lines[i][:1], lines[i][1:]
            if tag in (" ", "-"):
                if pos >= len(src) or src[pos] != body:
                    raise PatchError(f"context mismatch at line {pos + 1}")
                if tag == " ":
                    out.append(body)
                pos += 1
            elif tag == "+":
                out.append(body)
            elif tag != "\\":
                raise PatchError(f"unexpected patch line: {lines[i]!r}")
            i += 1
    out.extend(src[pos:])
    return "".join(out)


def split_patch(patch: str) -> dict[str, str]:
    """Split a multi-file patch (concatenated unified diffs) into {path: patch_text}."""
    parts: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in patch.splitlines(True):
        if line.startswith("--- a/"):
            current = parts.setdefault(line[6:].strip(), [])
        if current is not None:
            current.append(line)
    return {path: "".join(chunk) for path, chunk in parts.items()}


def apply_patch_set(files: dict[str, str], patch: str) -> dict[str, str]:
    """Apply a multi-file patch to a {path: text} mapping and return the new mapping."""
    result = dict(files)
    for path, text in split_patch(patch).items():
        if path not in result:
            raise PatchError(f"patch touches unknown file {path}")
        result[path] = apply_patch(result[path], text)
    return result
