"""Command line interface: `python -m taskforge build|verify`."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import pipeline, report
from .schema import Task


def cmd_build(args) -> int:
    cfg = pipeline.Config(
        single=args.single, compound=args.compound, pair_trials=args.pair_trials,
        seed=args.seed, solver_budget=args.solver_budget,
    )
    if args.workers:
        cfg.workers = args.workers
    start = time.time()
    print(f"taskforge: building from {args.seeds} (seed={cfg.seed}, workers={cfg.workers})")
    tasks, repo_stats, funnel = pipeline.build(Path(args.seeds), cfg)
    stats = report.build_stats(cfg, tasks, repo_stats, funnel)
    report.write_outputs(tasks, stats, Path(args.out), Path(args.site))
    t = stats["totals"]
    print(f"done in {time.time() - start:.0f}s: {t['tasks']} tasks, difficulty {stats['difficulty']}")
    print(f"wrote {args.out}/tasks.jsonl, stats.json, DATASET_CARD.md and {args.site}/data.js")
    return 0 if tasks else 1


def cmd_verify(args) -> int:
    path = Path(args.dataset)
    tasks = [Task.from_dict(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(pipeline.verify_task, tasks))
    bad = 0
    for task, problems in zip(tasks, results):
        status = "ok  " if not problems else "FAIL"
        bad += bool(problems)
        print(f"{status} {task.instance_id}" + ("" if not problems else "  " + "; ".join(problems)))
    print(f"\n{len(tasks) - bad}/{len(tasks)} tasks re-verified from {path}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taskforge", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="generate and validate the dataset")
    b.add_argument("--seeds", default="seeds", help="directory of seed repos")
    b.add_argument("--out", default="dataset")
    b.add_argument("--site", default="site", help="dashboard directory to receive data.js")
    b.add_argument("--single", type=int, default=8, help="single-bug tasks per repo")
    b.add_argument("--compound", type=int, default=3, help="two-bug tasks per repo")
    b.add_argument("--pair-trials", type=int, default=30)
    b.add_argument("--solver-budget", type=int, default=30)
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--workers", type=int, default=0)
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="re-check every task in a tasks.jsonl")
    v.add_argument("dataset", nargs="?", default="dataset/tasks.jsonl")
    v.add_argument("--workers", type=int, default=2)
    v.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
