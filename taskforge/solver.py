"""Reference solver used as a difficulty probe.

`SearchSolver` repairs a buggy snapshot using only what a developer would see: the source,
the tests and which tests fail. It localizes the fault with spectrum-based fault localization
(Ochiai over per-test line coverage), tries single-token edits on the most suspicious lines
first, and hill-climbs, accepting an edit only if it strictly shrinks the set of failing tests
(so it can never trade one broken test for another). The number of edit trials it needs
("attempts") is the difficulty signal: bugs on lines that failing tests share with many passing
tests are harder to localize, and compound bugs need several rounds.

Caveat: its action space is the same single-token catalogue the bug generator uses, so it is
a calibrated difficulty proxy and an under-specification detector, not a measure of how an LLM
would fare. To benchmark a model, implement the same `solve` signature and plug it in.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from . import mutators
from .sandbox import RunResult, run_tests


@dataclass
class SolveOutcome:
    solved: bool
    attempts: int
    final_files: dict


def ochiai(res: RunResult) -> dict[tuple, float]:
    """Suspiciousness per (file, line): ef / sqrt(total_failed * (ef + ep))."""
    failed, passed = set(res.failed), set(res.passed)
    ef: Counter = Counter()
    ep: Counter = Counter()
    for test_id, lines in res.coverage.items():
        bucket = ef if test_id in failed else ep if test_id in passed else None
        if bucket is not None:
            for fname, line in lines:
                bucket[(fname, line)] += 1
    total_failed = max(len(failed), 1)
    return {k: ef[k] / math.sqrt(total_failed * (ef[k] + ep[k])) for k in ef}


class SearchSolver:
    name = "sbfl-greedy-v1"

    def __init__(self, max_attempts: int = 30, timeout: float = 6.0):
        self.max_attempts = max_attempts
        self.timeout = timeout

    def solve(self, snapshot: dict, src_files: list, test_files: list, fail_to_pass: list) -> SolveOutcome:
        files = dict(snapshot)
        remaining, attempts, tried = len(fail_to_pass), 0, set()
        while remaining > 0 and attempts < self.max_attempts:
            observed = run_tests(files, timeout=self.timeout, coverage=True)
            if observed.status != "ok" or not observed.failed:
                break
            scores = ochiai(observed)
            ranked = []
            for f in src_files:
                for site in mutators.find_sites(files[f]):
                    ranked.append((-scores.get((f, site.row), 0.0), site.row, site.col, f, site))
            ranked.sort(key=lambda r: r[:4])
            improved = False
            for _, _, _, f, site in ranked:
                key = (f, site.row, site.col, site.replacement)
                if key in tried:
                    continue
                if attempts >= self.max_attempts:
                    break
                tried.add(key)
                attempts += 1
                trial = dict(files)
                trial[f] = mutators.apply_site(files[f], site)
                res = run_tests(trial, timeout=self.timeout)
                if res.status == "ok" and not res.collection_error and set(res.failed) < set(observed.failed):
                    files, remaining, improved = trial, len(res.failed), True
                    tried.clear()
                    break
            if not improved:
                break
        return SolveOutcome(remaining == 0, attempts, files)


def difficulty_tier(solved: bool, attempts: int) -> str:
    if solved and attempts <= 3:
        return "easy"
    if solved and attempts <= 10:
        return "medium"
    return "hard"
