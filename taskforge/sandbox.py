"""Run a file set's tests in an isolated temp directory.

Isolation is process-level: a fresh temp dir, a stripped environment, a wall-clock timeout
and (on POSIX) memory/file-size rlimits. It stops runaway mutants (infinite loops, huge
allocations) from hurting the host, but it is NOT a security boundary. Run untrusted code
in a container or VM.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

_LAUNCH = (
    "import sys, runpy\n"
    "try:\n"
    "    import resource\n"
    "    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))\n"
    "    resource.setrlimit(resource.RLIMIT_FSIZE, (8 << 20, 8 << 20))\n"
    "except Exception:\n"
    "    pass\n"
    "sys.argv = ['pytest'] + sys.argv[1:]\n"
    "runpy.run_module('pytest', run_name='__main__')\n"
)

# Injected as conftest.py when per-test line coverage is requested (used for fault localization).
_COVERAGE_CONFTEST = '''\
import json, os, sys
import pytest

_root = os.getcwd()
_src = {f for f in os.listdir(_root) if f.endswith(".py") and not f.startswith("test_") and f != "conftest.py"}
_hits = {}
_current = [None]


def _tracer(frame, event, arg):
    name = os.path.basename(frame.f_code.co_filename)
    if name not in _src:
        return None

    def local(frame, event, arg):
        if event == "line" and _current[0] is not None:
            _hits[_current[0]].add((name, frame.f_lineno))
        return local

    return local


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    _current[0] = item.nodeid
    _hits[item.nodeid] = set()
    sys.settrace(_tracer)
    try:
        yield
    finally:
        sys.settrace(None)
        _current[0] = None


def pytest_sessionfinish(session, exitstatus):
    with open(os.path.join(_root, "cov.json"), "w") as fh:
        json.dump({k: sorted(v) for k, v in _hits.items()}, fh)
'''


@dataclass
class RunResult:
    status: str  # "ok" | "timeout"
    passed: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)  # test id -> failure message
    details: dict[str, dict] = field(default_factory=dict)  # test id -> {"args": str, "check": str}
    coverage: dict[str, list] = field(default_factory=dict)  # test id -> [[file, line], ...]
    collection_error: bool = False
    seconds: float = 0.0

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.failed)

    @property
    def all_green(self) -> bool:
        return self.status == "ok" and not self.collection_error and not self.failed and bool(self.passed)


def environment_info() -> dict:
    import pytest

    return {
        "python": platform.python_version(),
        "pytest": pytest.__version__,
        "command": "python -m pytest -q",
    }


def _failure_details(name: str, text: str) -> dict:
    """Pull the parametrized inputs and the failing statement out of pytest's failure text."""
    lines = (text or "").splitlines()
    args = ""
    if "[" in name and lines and re.match(r"^\w+\s*=\s*", lines[0].strip()):
        block = []
        for ln in lines:
            if not ln.strip():
                break
            block.append(ln.strip())
        args = " ".join(block)
    check = next((ln[1:].strip() for ln in lines if ln.startswith(">")), "")
    return {"args": args[:300], "check": check[:200]}


def run_tests(
    files: dict[str, str],
    selectors: list[str] | None = None,
    timeout: float = 6.0,
    coverage: bool = False,
) -> RunResult:
    """Materialise `files` in a temp dir, run pytest, and return per-test outcomes."""
    with tempfile.TemporaryDirectory(prefix="tf_") as tmp:
        for rel, text in files.items():
            target = Path(tmp, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        if coverage:
            Path(tmp, "conftest.py").write_text(_COVERAGE_CONFTEST, encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "LANG": "C.UTF-8",
            "TMPDIR": tmp,
            "TEMP": tmp,
            "TMP": tmp,
        }
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
        cmd = [
            sys.executable, "-c", _LAUNCH,
            "-q", "-p", "no:cacheprovider", "-o", "addopts=", "-W", "ignore",
            "--junitxml=report.xml", *(selectors or []),
        ]
        start = time.perf_counter()
        try:
            proc = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return RunResult("timeout", seconds=time.perf_counter() - start)
        seconds = time.perf_counter() - start
        result = RunResult("ok", seconds=seconds, collection_error=proc.returncode in (2, 3, 4, 5))
        report = Path(tmp, "report.xml")
        if report.exists():
            try:
                root = ET.parse(report).getroot()
            except ET.ParseError:
                result.collection_error = True
                return result
            for case in root.iter("testcase"):
                classname, name = case.get("classname", ""), case.get("name", "")
                if not classname or not name.startswith("test"):
                    continue  # collection-level pseudo cases
                test_id = f"{classname.split('.')[0]}.py::{name}"
                problem = case.find("failure")
                if problem is None:
                    problem = case.find("error")
                if problem is not None:
                    result.failed[test_id] = (problem.get("message") or problem.text or "").strip()
                    result.details[test_id] = _failure_details(name, problem.text or "")
                elif case.find("skipped") is None:
                    result.passed.append(test_id)
        cov = Path(tmp, "cov.json")
        if coverage and cov.exists():
            try:
                result.coverage = json.loads(cov.read_text(encoding="utf-8"))
            except ValueError:
                pass
        return result
