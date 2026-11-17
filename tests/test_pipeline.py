import json
import shutil
from collections import Counter
from pathlib import Path

from taskforge import pipeline, report
from taskforge.cli import main
from taskforge.schema import Task

SEEDS = Path(__file__).parent.parent / "seeds"


def test_end_to_end_small_build_is_valid_and_reverifiable(tmp_path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    shutil.copytree(SEEDS / "lrucache", seeds / "lrucache")
    cfg = pipeline.Config(single=3, compound=1, pair_trials=6, solver_budget=12)
    tasks, repo_stats, funnel = pipeline.build(seeds, cfg, log=lambda _: None)

    assert len(tasks) >= 2
    assert funnel["accepted"] == len(tasks)
    for t in tasks:
        assert t.fail_to_pass and t.pass_to_pass
        assert t.patch.startswith("--- a/")
        assert not set(t.fail_to_pass) & set(t.pass_to_pass)
        assert t.difficulty["tier"] in {"easy", "medium", "hard"}

    stats = report.build_stats(cfg, tasks, repo_stats, Counter(funnel))
    report.write_outputs(tasks, stats, tmp_path / "out", tmp_path / "site")
    assert (tmp_path / "site" / "data.js").read_text().startswith("window.TASKFORGE = ")
    assert "snapshot" not in (tmp_path / "site" / "data.js").read_text()
    assert "Dataset card" in (tmp_path / "out" / "DATASET_CARD.md").read_text()

    jsonl = tmp_path / "out" / "tasks.jsonl"
    assert main(["verify", str(jsonl)]) == 0


def test_verify_detects_a_tampered_patch(tmp_path):
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    shutil.copytree(SEEDS / "lrucache", seeds / "lrucache")
    cfg = pipeline.Config(single=1, compound=0, pair_trials=0, solver_budget=6)
    tasks, _, _ = pipeline.build(seeds, cfg, log=lambda _: None)
    task = tasks[0]
    assert pipeline.verify_task(task) == []

    broken = Task.from_dict(json.loads(task.to_json()))
    lines = broken.patch.splitlines(True)
    i = next(n for n, ln in enumerate(lines) if ln.startswith("-") and not ln.startswith("---"))
    lines[i] = "-this line is not in the source\n"
    broken.patch = "".join(lines)
    assert any("does not apply" in p for p in pipeline.verify_task(broken))
