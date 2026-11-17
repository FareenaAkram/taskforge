from pathlib import Path

import pytest

from taskforge.pipeline import load_seed
from taskforge.sandbox import run_tests

SEEDS = sorted(p for p in (Path(__file__).parent.parent / "seeds").iterdir() if p.is_dir())


@pytest.mark.parametrize("path", SEEDS, ids=lambda p: p.name)
def test_seed_passes_its_own_tests_and_is_substantial(path):
    seed = load_seed(path)
    res = run_tests(seed.files, timeout=30)
    assert res.all_green, res.failed
    assert res.total >= 25
