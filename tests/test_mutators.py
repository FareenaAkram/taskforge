import pytest

from taskforge import mutators

SRC = '''def f(a, b):
    """a < b is documented here and must never be mutated."""
    # a < b in a comment is ignored too
    s = "x + y"
    if a < b and a != 0:
        return a + 1
    return min(a, b)  # nomutate
'''


def sites():
    return mutators.find_sites(SRC)


def test_strings_comments_and_nomutate_lines_are_skipped():
    rows = {s.row for s in sites()}
    assert not rows & {2, 3, 4, 7}


def test_expected_sites_on_code_line():
    found = {(s.original, s.replacement) for s in sites() if s.row == 5}
    assert {("<", "<="), ("and", "or"), ("!=", "=="), ("0", "1")} <= found


def test_off_by_one_does_not_go_below_zero():
    zeros = [s for s in sites() if s.row == 5 and s.original == "0"]
    assert [s.replacement for s in zeros] == ["1"]


@pytest.mark.parametrize("s", sites(), ids=lambda s: f"{s.row}:{s.original}->{s.replacement}")
def test_apply_changes_exactly_one_token(s):
    out = mutators.apply_site(SRC, s)
    diff = [(a, b) for a, b in zip(SRC.splitlines(), out.splitlines()) if a != b]
    assert len(diff) == 1
    assert out.splitlines()[s.row - 1].count(s.replacement) >= 1
    compile(out, "<mutant>", "exec")


def test_apply_sites_right_to_left_keeps_offsets_valid():
    a, b = [s for s in sites() if s.row == 5][:2]
    out = mutators.apply_sites(SRC, [a, b])
    line = out.splitlines()[4]
    assert a.replacement in line and b.replacement in line


def test_mismatched_site_is_rejected():
    s = sites()[0]
    with pytest.raises(ValueError):
        mutators.apply_site("totally different\n" * 10, s)


def test_unparseable_source_yields_no_sites():
    assert mutators.find_sites("x = (1 +\n") == []
