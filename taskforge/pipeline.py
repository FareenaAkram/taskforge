"""Mine -> screen -> sample -> validate -> quality-check -> probe difficulty -> export."""

from __future__ import annotations

import os
import random
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import analysis, issue, mutators, patching
from .sandbox import RunResult, environment_info, run_tests
from .schema import Task
from .solver import SearchSolver, difficulty_tier


@dataclass
class Config:
    single: int = 8  # single-bug tasks per repo
    compound: int = 3  # two-bug tasks per repo
    pair_trials: int = 30  # random bug pairs to try per repo
    seed: int = 7
    workers: int = field(default_factory=lambda: max(2, os.cpu_count() or 2))
    timeout: float = 4.0
    max_fail_ratio: float = 0.6  # reject bugs that break most of the suite (too obvious)
    solver_budget: int = 30


@dataclass
class Seed:
    name: str
    files: dict
    src_files: list
    test_files: list


@dataclass
class Candidate:
    seed: Seed
    edits: list  # [(file, Site)]
    result: RunResult

    @property
    def kinds(self) -> list:
        return sorted({s.kind for _, s in self.edits})


def load_seed(path: Path) -> Seed:
    files = {p.name: p.read_text(encoding="utf-8") for p in sorted(path.glob("*.py"))}
    tests = [n for n in files if n.startswith("test_")]
    src = [n for n in files if n not in tests and n != "conftest.py"]
    return Seed(path.name, files, src, tests)


def apply_edits(files: dict, edits: list) -> dict:
    out = dict(files)
    by_file = defaultdict(list)
    for fname, site in edits:
        by_file[fname].append(site)
    for fname, sites in by_file.items():
        out[fname] = mutators.apply_sites(out[fname], sites)
    return out


def pmap(fn: Callable, items: list, workers: int) -> list:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def classify(res: RunResult, total: int, max_ratio: float) -> str:
    if res.status == "timeout":
        return "timeout"
    if res.collection_error:
        return "collection_error"
    if not res.failed:
        return "survived"
    if len(res.failed) / max(total, 1) > max_ratio:
        return "too_broad"
    return "candidate"


def pick(cands: list, limit: int, rng: random.Random) -> tuple[list, int]:
    """One candidate per distinct failure signature, then round-robin across mutation kinds."""
    groups = defaultdict(list)
    for c in cands:
        groups[(len(c.edits), tuple(sorted(c.result.failed)))].append(c)
    reps = [rng.choice(groups[k]) for k in sorted(groups)]
    by_kind = defaultdict(list)
    for c in reps:
        by_kind[c.kinds[0]].append(c)
    for bucket in by_kind.values():
        rng.shuffle(bucket)
    chosen: list = []
    kinds = sorted(by_kind)
    while len(chosen) < limit and any(by_kind.values()):
        for k in kinds:
            if by_kind[k] and len(chosen) < limit:
                chosen.append(by_kind[k].pop())
    return chosen, len(reps)


def validate(cand: Candidate, baseline: RunResult, docs: dict, cfg: Config):
    """Full validation of one candidate. Returns (record_or_None, reject_reason_or_None)."""
    seed = cand.seed
    buggy = apply_edits(seed.files, cand.edits)
    again = run_tests(buggy, timeout=cfg.timeout)
    if set(again.failed) != set(cand.result.failed):
        return None, "flaky"
    changed = [f for f in seed.src_files if buggy[f] != seed.files[f]]
    patch = "".join(patching.make_patch(buggy[f], seed.files[f], f) for f in changed)
    try:
        fixed = patching.apply_patch_set(buggy, patch)
    except patching.PatchError:
        return None, "patch_roundtrip"
    if fixed != seed.files:
        return None, "patch_roundtrip"
    after = run_tests(fixed, timeout=cfg.timeout)
    if not after.all_green or set(after.passed) != set(baseline.passed):
        return None, "golden_fails"
    statement = issue.write_issue(seed.name, cand.result.failed, cand.result.details, docs)
    if issue.leaks(statement, patch):
        return None, "leaky_issue"
    changed_lines = sum(1 for ln in patch.splitlines() if ln[:1] in ("+", "-") and not ln.startswith(("+++", "---"))) // 2
    return {
        "buggy": buggy,
        "patch": patch,
        "statement": statement,
        "after": after,
        "changed_lines": changed_lines,
    }, None


def process_seed(seed: Seed, cfg: Config, funnel: Counter, log: Callable[[str], None]) -> tuple[list, dict]:
    baseline = run_tests(seed.files, timeout=30)
    if not baseline.all_green:
        raise RuntimeError(f"seed {seed.name!r} does not pass its own tests: {baseline.failed}")
    total = baseline.total
    rng = random.Random(f"{cfg.seed}:{seed.name}")
    docs: dict = {}
    for t in seed.test_files:
        docs.update(analysis.test_docstrings(seed.files[t]))

    # 1) mine + screen every single-token mutant
    jobs = [(f, s) for f in seed.src_files for s in mutators.find_sites(seed.files[f])]
    results = pmap(lambda j: run_tests(apply_edits(seed.files, [j]), timeout=cfg.timeout), jobs, cfg.workers)
    singles, reasons = [], Counter()
    for job, res in zip(jobs, results):
        verdict = classify(res, total, cfg.max_fail_ratio)
        reasons[verdict] += 1
        if verdict == "candidate":
            singles.append(Candidate(seed, [job], res))
    killed = len(jobs) - reasons["survived"]
    log(f"  {seed.name}: {len(jobs)} mutants -> {len(singles)} usable ({reasons['survived']} survived the tests)")

    # 2) compound (two independent bugs in different functions)
    spans = {f: analysis.function_spans(seed.files[f]) for f in seed.src_files}
    pair_jobs, seen, tries = [], set(), 0
    while len(pair_jobs) < cfg.pair_trials and tries < cfg.pair_trials * 30 and len(singles) >= 2:
        tries += 1
        a, b = rng.sample(singles, 2)
        (fa, sa), (fb, sb) = a.edits[0], b.edits[0]
        fn_a = analysis.enclosing_function(spans[fa], sa.row)
        fn_b = analysis.enclosing_function(spans[fb], sb.row)
        if fn_a is None or fn_a == fn_b:
            continue
        key = tuple(sorted([(fa, sa.row, sa.col, sa.replacement), (fb, sb.row, sb.col, sb.replacement)]))
        if key not in seen:
            seen.add(key)
            pair_jobs.append([a.edits[0], b.edits[0]])
    pair_results = pmap(lambda e: run_tests(apply_edits(seed.files, e), timeout=cfg.timeout), pair_jobs, cfg.workers)
    compounds = []
    for edits, res in zip(pair_jobs, pair_results):
        if classify(res, total, cfg.max_fail_ratio) == "candidate":
            compounds.append(Candidate(seed, edits, res))
    funnel["compound_trials"] += len(pair_jobs)
    funnel["compound_usable"] += len(compounds)

    # 3) dedupe by failure signature + stratified sample
    chosen_s, uniq_s = pick(singles, cfg.single, rng)
    chosen_c, uniq_c = pick(compounds, cfg.compound, rng)
    chosen = chosen_s + chosen_c
    funnel["mutants"] += len(jobs)
    funnel["survived"] += reasons["survived"]
    funnel["timeout"] += reasons["timeout"]
    funnel["collection_error"] += reasons["collection_error"]
    funnel["too_broad"] += reasons["too_broad"]
    funnel["usable"] += len(singles) + len(compounds)
    funnel["duplicate_signature"] += (len(singles) - uniq_s) + (len(compounds) - uniq_c)
    funnel["not_sampled"] += (uniq_s - len(chosen_s)) + (uniq_c - len(chosen_c))

    # 4) validate (re-run for flakiness, apply golden patch, quality checks)
    checked = pmap(lambda c: validate(c, baseline, docs, cfg), chosen, cfg.workers)
    solver = SearchSolver(max_attempts=cfg.solver_budget, timeout=cfg.timeout)
    accepted = []
    for cand, (rec, why) in zip(chosen, checked):
        if rec is None:
            funnel[why] += 1
        else:
            accepted.append((cand, rec))

    # 5) difficulty probe
    outcomes = pmap(
        lambda cr: solver.solve(cr[1]["buggy"], seed.src_files, seed.test_files, sorted(cr[0].result.failed)),
        accepted,
        cfg.workers,
    )
    env = environment_info()
    tasks = []
    ordered = sorted(zip(accepted, outcomes), key=lambda x: (len(x[0][0].edits), x[0][0].edits[0][1].row))
    for i, ((cand, rec), out) in enumerate(ordered, 1):
        exact = out.solved and all(out.final_files[f] == seed.files[f] for f in seed.src_files)
        tasks.append(
            Task(
                instance_id=f"tf-{seed.name}-{i:03d}",
                repo=seed.name,
                bug_count=len(cand.edits),
                mutation_kinds=cand.kinds,
                problem_statement=rec["statement"],
                patch=rec["patch"],
                snapshot=rec["buggy"],
                test_files=list(seed.test_files),
                fail_to_pass=sorted(cand.result.failed),
                pass_to_pass=sorted(cand.result.passed),
                environment=env,
                validation={
                    "buggy_runs": 2,
                    "stable": True,
                    "golden_patch_applies": True,
                    "golden_patch_all_green": True,
                    "tests_total": total,
                },
                quality={
                    "issue_leaks_patch": False,
                    "issue_chars": len(rec["statement"]),
                    "changed_lines": rec["changed_lines"],
                    "alternative_fix_found": bool(out.solved and not exact),
                },
                difficulty={
                    "tier": difficulty_tier(out.solved, out.attempts),
                    "solver": solver.name,
                    "solved": out.solved,
                    "attempts": out.attempts,
                },
            )
        )
    funnel["accepted"] += len(tasks)
    loc = sum(len(seed.files[f].splitlines()) for f in seed.src_files)
    stats = {
        "name": seed.name,
        "loc": loc,
        "tests": total,
        "mutants": len(jobs),
        "killed": killed,
        "mutation_score": round(killed / max(len(jobs), 1), 3),
        "tasks": len(tasks),
    }
    return tasks, stats


def build(seeds_dir: Path, cfg: Config, log: Callable[[str], None] = print) -> tuple[list, list, Counter]:
    funnel: Counter = Counter()
    all_tasks, repo_stats = [], []
    for path in sorted(p for p in seeds_dir.iterdir() if p.is_dir()):
        seed = load_seed(path)
        if not seed.src_files or not seed.test_files:
            continue
        tasks, stats = process_seed(seed, cfg, funnel, log)
        all_tasks += tasks
        repo_stats.append(stats)
    return all_tasks, repo_stats, funnel


def verify_task(task: Task, timeout: float = 10.0) -> list[str]:
    """Re-check a task from its JSONL record alone. Returns a list of problems (empty = OK)."""
    problems = []
    before = run_tests(task.snapshot, timeout=timeout)
    if set(before.failed) != set(task.fail_to_pass):
        problems.append("fail_to_pass mismatch on the buggy snapshot")
    if sorted(before.passed) != sorted(task.pass_to_pass):
        problems.append("pass_to_pass mismatch on the buggy snapshot")
    try:
        fixed = patching.apply_patch_set(task.snapshot, task.patch)
    except patching.PatchError as exc:
        return problems + [f"golden patch does not apply: {exc}"]
    after = run_tests(fixed, timeout=timeout)
    if not after.all_green:
        problems.append("tests still fail after the golden patch")
    elif set(after.passed) != set(task.fail_to_pass) | set(task.pass_to_pass):
        problems.append("test set changed after the golden patch")
    return problems
