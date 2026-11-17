"""Token-level bug injection.

Mutations are applied to exact token positions found with `tokenize`, so the diff between
the clean and the buggy file is always a minimal, human-readable change and formatting is
never disturbed (unlike round-tripping through `ast.unparse`).
"""

from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass

# token string -> (replacement, mutation kind)
_SWAPS = {
    "<": ("<=", "comparison_boundary"),
    "<=": ("<", "comparison_boundary"),
    ">": (">=", "comparison_boundary"),
    ">=": (">", "comparison_boundary"),
    "==": ("!=", "comparison_negation"),
    "!=": ("==", "comparison_negation"),
    "+": ("-", "arithmetic_operator"),
    "-": ("+", "arithmetic_operator"),
    "+=": ("-=", "augmented_assignment"),
    "-=": ("+=", "augmented_assignment"),
    "and": ("or", "boolean_logic"),
    "or": ("and", "boolean_logic"),
    "True": ("False", "boolean_constant"),
    "False": ("True", "boolean_constant"),
    "min": ("max", "min_max_swap"),
    "max": ("min", "min_max_swap"),
}

KINDS = sorted({kind for _, kind in _SWAPS.values()} | {"off_by_one"})


@dataclass(frozen=True)
class Site:
    """One single-token edit: replace `original` at (row, col..end_col) with `replacement`."""

    row: int  # 1-based
    col: int
    end_col: int
    original: str
    replacement: str
    kind: str

    def describe(self) -> str:
        return f"line {self.row}: {self.original!r} -> {self.replacement!r} ({self.kind})"


def find_sites(source: str) -> list[Site]:
    """Every single-token mutation available in `source`, in source order."""
    sites: list[Site] = []
    lines = source.splitlines()
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return sites
    for tok in tokens:
        if tok.type not in (tokenize.OP, tokenize.NAME, tokenize.NUMBER):
            continue
        row, col = tok.start
        end_row, end_col = tok.end
        if row != end_row or "nomutate" in lines[row - 1]:
            continue
        text = tok.string
        if tok.type == tokenize.NUMBER:
            if text.isdigit() and int(text) <= 99:
                n = int(text)
                sites.append(Site(row, col, end_col, text, str(n + 1), "off_by_one"))
                if n > 0:
                    sites.append(Site(row, col, end_col, text, str(n - 1), "off_by_one"))
            continue
        if text in _SWAPS:
            replacement, kind = _SWAPS[text]
            sites.append(Site(row, col, end_col, text, replacement, kind))
    return sites


def apply_site(source: str, site: Site) -> str:
    """Return `source` with `site` applied."""
    lines = source.splitlines(True)
    line = lines[site.row - 1]
    if line[site.col : site.end_col] != site.original:
        raise ValueError(f"site does not match source: {site.describe()}")
    lines[site.row - 1] = line[: site.col] + site.replacement + line[site.end_col :]
    return "".join(lines)


def apply_sites(source: str, sites: list[Site]) -> str:
    """Apply several sites to one file (right-to-left so column offsets stay valid)."""
    for site in sorted(sites, key=lambda s: (s.row, s.col), reverse=True):
        source = apply_site(source, site)
    return source
