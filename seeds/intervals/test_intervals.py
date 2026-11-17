import pytest

from intervals import (contains_point, find_gaps, insert_interval, intersect,
                       max_overlap, merge_intervals, total_covered)


@pytest.mark.parametrize(
    "given,expected",
    [
        ([], []),
        ([[1, 3]], [[1, 3]]),
        ([[1, 3], [2, 6], [8, 10]], [[1, 6], [8, 10]]),
        ([[1, 4], [4, 5]], [[1, 5]]),
        ([[5, 6], [1, 2]], [[1, 2], [5, 6]]),
        ([[1, 10], [2, 3]], [[1, 10]]),
        ([[1, 2], [3, 4]], [[1, 2], [3, 4]]),
        ([[1, 4], [0, 2], [3, 5]], [[0, 5]]),
        ([[2, 3], [2, 5]], [[2, 5]]),
        ([[1, 5], [3, 4], [2, 9]], [[1, 9]]),
    ],
    ids=["empty", "single", "overlap", "touching", "unsorted", "contained", "gap", "chain", "same_start", "nested"],
)
def test_merge_intervals(given, expected):
    """Overlapping and touching intervals are merged into sorted disjoint ranges"""
    assert merge_intervals(given) == expected


def test_merge_does_not_modify_input():
    """Merging leaves the caller's list, and the lists inside it, untouched"""
    data = [[3, 4], [1, 2], [2, 3]]
    out = merge_intervals(data)
    out[0][0] = 99
    assert data == [[3, 4], [1, 2], [2, 3]]


@pytest.mark.parametrize(
    "given,new,expected",
    [
        ([[1, 3], [6, 9]], [2, 5], [[1, 5], [6, 9]]),
        ([[1, 2], [3, 5], [6, 7], [8, 10], [12, 16]], [4, 8], [[1, 2], [3, 10], [12, 16]]),
        ([], [5, 7], [[5, 7]]),
        ([[1, 2]], [3, 4], [[1, 2], [3, 4]]),
        ([[3, 4]], [1, 2], [[1, 2], [3, 4]]),
        ([[1, 5]], [2, 3], [[1, 5]]),
        ([[1, 2]], [2, 3], [[1, 3]]),
        ([[1, 2], [5, 6]], [3, 4], [[1, 2], [3, 4], [5, 6]]),
        ([[1, 2]], [8, 9], [[1, 2], [8, 9]]),
        ([[3, 4]], [1, 3], [[1, 4]]),
    ],
    ids=["merge_right", "merge_many", "empty", "after", "before", "inside", "touch_end", "between", "far_after", "touch_start"],
)
def test_insert_interval(given, new, expected):
    """Inserting keeps the list sorted and merges every interval the new one touches"""
    assert insert_interval(given, new) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (
            [[0, 2], [5, 10], [13, 23], [24, 25]],
            [[1, 5], [8, 12], [15, 24], [25, 26]],
            [[1, 2], [5, 5], [8, 10], [15, 23], [24, 24], [25, 25]],
        ),
        ([], [[1, 2]], []),
        ([[1, 2]], [[3, 4]], []),
        ([[1, 5]], [[1, 5]], [[1, 5]]),
        ([[1, 10]], [[2, 3], [5, 6]], [[2, 3], [5, 6]]),
        ([[2, 3], [5, 6]], [[1, 10]], [[2, 3], [5, 6]]),
    ],
    ids=["classic", "empty", "disjoint", "identical", "contains", "contained"],
)
def test_intersect(a, b, expected):
    """Intersection returns the shared sub-ranges, including single shared points"""
    assert intersect(a, b) == expected


@pytest.mark.parametrize(
    "given,expected",
    [([[1, 3], [2, 6]], 5), ([], 0), ([[1, 2], [3, 4]], 2), ([[0, 10], [2, 3]], 10), ([[5, 5]], 0)],
    ids=["overlap", "empty", "gap", "contained", "point"],
)
def test_total_covered(given, expected):
    """Total coverage counts overlapping stretches once"""
    assert total_covered(given) == expected


@pytest.mark.parametrize(
    "given,lo,hi,expected",
    [
        ([[2, 4], [6, 8]], 0, 10, [[0, 2], [4, 6], [8, 10]]),
        ([], 0, 5, [[0, 5]]),
        ([[0, 10]], 0, 10, []),
        ([[-5, 3]], 0, 10, [[3, 10]]),
        ([[2, 4]], 0, 3, [[0, 2]]),
        ([[8, 12]], 0, 10, [[0, 8]]),
        ([[3, 5], [4, 9]], 1, 12, [[1, 3], [9, 12]]),
        ([[0, 3]], 0, 10, [[3, 10]]),
        ([[-5, -1]], 0, 3, [[0, 3]]),
        ([[6, 8], [2, 4]], 0, 10, [[0, 2], [4, 6], [8, 10]]),
    ],
    ids=["middle", "empty", "full", "left_overhang", "right_overhang", "right_edge", "merged", "starts_at_lo", "outside", "unsorted"],
)
def test_find_gaps(given, lo, hi, expected):
    """Gaps are the parts of [lo, hi] that no interval covers"""
    assert find_gaps(given, lo, hi) == expected


@pytest.mark.parametrize(
    "x,expected",
    [(1, True), (3, True), (4, False), (7, True), (0, False), (8, False), (5, True)],
    ids=["start", "end", "between", "end2", "before", "after", "start2"],
)
def test_contains_point(x, expected):
    """Closed intervals include both of their endpoints"""
    assert contains_point([[1, 3], [5, 7]], x) is expected


def test_contains_point_empty():
    """No intervals means no point is contained"""
    assert contains_point([], 1) is False


@pytest.mark.parametrize(
    "given,expected",
    [
        ([], 0),
        ([[1, 2]], 1),
        ([[1, 3], [2, 4], [3, 5]], 3),
        ([[1, 2], [3, 4]], 1),
        ([[1, 2], [2, 3]], 2),
        ([[1, 10], [2, 3], [4, 5], [4, 6]], 3),
        ([[0, 0], [0, 0]], 2),
    ],
    ids=["empty", "single", "triple", "disjoint", "touching", "nested", "points"],
)
def test_max_overlap(given, expected):
    """Max overlap is the highest number of closed intervals sharing one point"""
    assert max_overlap(given) == expected
