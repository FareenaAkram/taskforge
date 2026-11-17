"""Turn raw failing-test output into a developer-facing problem statement, and check it for leaks."""

from __future__ import annotations

MAX_SCENARIOS = 4


def _base(test_id: str) -> str:
    return test_id.split("::")[-1].split("[")[0]


def _case(test_id: str) -> str:
    name = test_id.split("::")[-1]
    return name[name.index("[") + 1 : -1] if "[" in name else ""


def _humanize(test_id: str) -> str:
    name = _base(test_id)
    if name.startswith("test_"):
        name = name[5:]
    return name.replace("_", " ")


def _clean(message: str) -> list[str]:
    lines = [ln.rstrip() for ln in message.strip().splitlines() if ln.strip()]
    return [ln[:160] for ln in lines[:3]]


def write_issue(module: str, failures: dict[str, str], details: dict[str, dict], docs: dict[str, str]) -> str:
    """Problem statement built only from observable behaviour: test docs, inputs, assertion output."""
    ids = sorted(failures)
    title = (docs.get(_base(ids[0])) or _humanize(ids[0])).rstrip(".")
    many = len(ids) > 1
    out = [
        f"## `{module}`: {title}",
        "",
        f"After a recent change, {'several documented behaviours' if many else 'a documented behaviour'} "
        f"in `{module}` no longer work as expected.",
        "",
    ]
    for i, test_id in enumerate(ids[:MAX_SCENARIOS], 1):
        label = (docs.get(_base(test_id)) or _humanize(test_id)).rstrip(".")
        case = _case(test_id)
        info = details.get(test_id, {})
        out.append(f"{i}. **{label}**" + (f" (case `{case}`)" if case else ""))
        if info.get("args"):
            out.append(f"   - inputs: `{info['args']}`")
        if info.get("check"):
            out.append(f"   - check: `{info['check']}`")
        out += ["   ```", *("   " + ln for ln in _clean(failures[test_id])), "   ```"]
    if len(ids) > MAX_SCENARIOS:
        out.append(f"\n...and {len(ids) - MAX_SCENARIOS} more failing scenario(s) in the test suite.")
    out += ["", "Please find the root cause and fix it without breaking any currently passing behaviour."]
    return "\n".join(out)


def leaks(statement: str, patch: str) -> bool:
    """True if a changed line of the golden patch appears verbatim in the problem statement."""
    for line in patch.splitlines():
        if line.startswith(("+++", "---")) or line[:1] not in ("+", "-"):
            continue
        body = line[1:].strip()
        if len(body) >= 8 and body in statement:
            return True
    return False
