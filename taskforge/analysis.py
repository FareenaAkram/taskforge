"""Static helpers: function spans and test docstrings."""

from __future__ import annotations

import ast


def function_spans(source: str) -> list[tuple[str, int, int]]:
    """(name, first_line, last_line) for every function in the module."""
    spans = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append((node.name, node.lineno, node.end_lineno or node.lineno))
    return spans


def enclosing_function(spans: list[tuple[str, int, int]], line: int) -> str | None:
    """Innermost function containing `line`, or None for module-level code."""
    best = None
    for name, start, end in spans:
        if start <= line <= end and (best is None or end - start < best[2] - best[1]):
            best = (name, start, end)
    return best[0] if best else None


def test_docstrings(test_source: str) -> dict[str, str]:
    """{test function name: first docstring line}."""
    docs = {}
    for node in ast.walk(ast.parse(test_source)):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            doc = ast.get_docstring(node)
            if doc:
                docs[node.name] = doc.strip().splitlines()[0].strip()
    return docs
