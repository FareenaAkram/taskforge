"""Aggregate statistics and write the dataset, dataset card and dashboard data."""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path

from . import __version__
from .pipeline import Config
from .schema import Task

FUNNEL_ORDER = [
    ("mutants", "Candidate bugs injected"),
    ("survived", "Rejected: tests do not notice (equivalent or untested)"),
    ("timeout", "Rejected: infinite loop / timeout"),
    ("collection_error", "Rejected: crashes test collection"),
    ("too_broad", "Rejected: breaks most of the suite"),
    ("usable", "Usable single + two-bug candidates"),
    ("duplicate_signature", "Dropped: same failing-test signature as another task"),
    ("not_sampled", "Dropped: over the per-repo quota"),
    ("flaky", "Rejected: unstable across re-runs"),
    ("patch_roundtrip", "Rejected: patch did not round-trip"),
    ("golden_fails", "Rejected: golden patch left tests failing"),
    ("leaky_issue", "Rejected: issue text leaked the fix"),
    ("accepted", "Accepted tasks"),
]


def build_stats(cfg: Config, tasks: list[Task], repo_stats: list[dict], funnel: Counter) -> dict:
    from .sandbox import environment_info
    from .solver import SearchSolver

    n = max(len(tasks), 1)
    return {
        "meta": {
            "version": __version__,
            "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "seed": cfg.seed,
            "solver": SearchSolver.name,
            **environment_info(),
        },
        "totals": {
            "tasks": len(tasks),
            "repos": len(repo_stats),
            "avg_fail_to_pass": round(sum(len(t.fail_to_pass) for t in tasks) / n, 1),
            "avg_pass_to_pass": round(sum(len(t.pass_to_pass) for t in tasks) / n, 1),
            "solver_solved": round(sum(t.difficulty["solved"] for t in tasks) / n, 3),
            "alternative_fix_rate": round(sum(t.quality["alternative_fix_found"] for t in tasks) / n, 3),
            "mutation_score": round(
                sum(r["killed"] for r in repo_stats) / max(sum(r["mutants"] for r in repo_stats), 1), 3
            ),
        },
        "funnel": [{"key": k, "label": label, "count": funnel.get(k, 0)} for k, label in FUNNEL_ORDER],
        "repos": repo_stats,
        "difficulty": dict(Counter(t.difficulty["tier"] for t in tasks)),
        "kinds": dict(Counter(k for t in tasks for k in t.mutation_kinds)),
        "bug_counts": dict(Counter(t.bug_count for t in tasks)),
    }


def dataset_card(stats: dict) -> str:
    m, t = stats["meta"], stats["totals"]
    rows = "\n".join(f"| {f['label']} | {f['count']} |" for f in stats["funnel"])
    repos = "\n".join(
        f"| `{r['name']}` | {r['loc']} | {r['tests']} | {r['mutants']} | {r['mutation_score']:.0%} | {r['tasks']} |"
        for r in stats["repos"]
    )
    diff = ", ".join(f"{k}: {v}" for k, v in sorted(stats["difficulty"].items()))
    kinds = ", ".join(f"{k}: {v}" for k, v in sorted(stats["kinds"].items()))
    return f"""# Dataset card: taskforge-bench v{m['version']}

{t['tasks']} executable bug-fix tasks across {t['repos']} small Python repositories, generated {m['generated_at']}
(seed {m['seed']}, Python {m['python']}, pytest {m['pytest']}).

## What a record contains

| Field | Meaning |
|---|---|
| `instance_id` | Stable id, `tf-<repo>-<n>` |
| `problem_statement` | Developer-facing description built from observable failures only |
| `snapshot` | Full buggy repo (source and tests) as `{{path: text}}` |
| `patch` | Golden unified diff (source files only) |
| `fail_to_pass` | Tests that fail on the snapshot and pass after the golden patch |
| `pass_to_pass` | Tests that must keep passing (regression guard) |
| `bug_count` / `mutation_kinds` | 1 or 2 injected bugs and their categories |
| `difficulty` | Tier plus the reference solver's attempts (see below) |
| `quality`, `validation` | Checks every task passed |

## How tasks are made and checked

1. Every single-token mutation of each clean repo is injected and run against the suite.
2. Bugs the tests cannot see, that hang, or that break most of the suite are rejected.
3. Survivors are de-duplicated by failing-test signature and sampled across mutation kinds.
   Some are combined into two-bug tasks (different functions, so both fixes are required).
4. Each candidate is re-run to rule out flakiness, the golden patch is applied with a
   context-verifying patcher, and the full suite must go green with the exact original test set.
5. The problem statement must not contain any changed line of the patch.
6. A reference solver (spectrum-based fault localization with Ochiai scores over per-test line
   coverage, then greedy single-token repair) gives a difficulty tier from the number of edit
   trials it needs: easy <= 3, medium <= 10, otherwise hard (including unsolved within budget).

`python -m taskforge verify dataset/tasks.jsonl` re-checks all of this from the JSONL alone.

## Funnel

| Stage | Count |
|---|---|
{rows}

## Repositories

`Mutation score` = share of injected bugs the repo's own tests detect.

| Repo | LOC | Tests | Mutants | Mutation score | Tasks |
|---|---|---|---|---|---|
{repos}

## Distributions

- Difficulty: {diff}
- Mutation kinds: {kinds}
- Mean fail-to-pass tests per task: {t['avg_fail_to_pass']}; mean pass-to-pass: {t['avg_pass_to_pass']}
- Reference solver solved {t['solver_solved']:.0%} of tasks; {t['alternative_fix_rate']:.0%} of tasks admit a valid fix that differs from the golden patch.

## Limitations

- Bugs are synthetic single-token mutations, not mined from real commit history.
- The reference solver shares the generator's edit catalogue, so tiers are a calibrated
  proxy for difficulty, not a measure of how a language model would perform.
- Problem statements are generated from test output; they are accurate but terse.
- Sandboxing is process-level (temp dir, timeout, rlimits), not a security boundary.
"""


def write_outputs(tasks: list[Task], stats: dict, out_dir: Path, site_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    site_dir.mkdir(parents=True, exist_ok=True)
    jsonl = "\n".join(t.to_json() for t in tasks) + "\n"
    (out_dir / "tasks.jsonl").write_text(jsonl, encoding="utf-8")
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    (out_dir / "DATASET_CARD.md").write_text(dataset_card(stats), encoding="utf-8")
    (site_dir / "tasks.jsonl").write_text(jsonl, encoding="utf-8")
    slim = []
    for t in tasks:
        d = t.to_dict()
        d.pop("snapshot")
        slim.append(d)
    payload = {"stats": stats, "tasks": slim}
    (site_dir / "data.js").write_text(
        "window.TASKFORGE = " + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8"
    )
