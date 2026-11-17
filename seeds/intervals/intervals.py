"""intervals: operations on closed [start, end] integer intervals."""


def merge_intervals(intervals):
    """Merge overlapping or touching intervals and return them sorted."""
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda iv: iv[0])
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return merged


def insert_interval(intervals, new):
    """Insert `new` into a sorted, non-overlapping list, merging as needed."""
    result = []
    start, end = new
    placed = False
    for lo, hi in intervals:
        if hi < start:
            result.append([lo, hi])
        elif lo > end:
            if not placed:
                result.append([start, end])
                placed = True
            result.append([lo, hi])
        else:
            start = min(start, lo)
            end = max(end, hi)
    if not placed:
        result.append([start, end])
    return result


def intersect(a, b):
    """Intersection of two sorted, non-overlapping interval lists."""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if lo <= hi:
            out.append([lo, hi])
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def total_covered(intervals):
    """Total length covered by the union of the intervals."""
    return sum(end - start for start, end in merge_intervals(intervals))


def find_gaps(intervals, lo, hi):
    """Sub-ranges of [lo, hi] not covered by any interval."""
    gaps = []
    cursor = lo
    for start, end in merge_intervals(intervals):
        if end <= cursor:
            continue
        if start > cursor:
            gaps.append([cursor, min(start, hi)])
        cursor = max(cursor, end)
        if cursor >= hi:
            break
    if cursor < hi:
        gaps.append([cursor, hi])
    return gaps


def contains_point(intervals, x):
    """True if x lies inside any closed interval."""
    return any(start <= x <= end for start, end in intervals)


def max_overlap(intervals):
    """Largest number of intervals that share a single point (closed intervals)."""
    events = []
    for start, end in intervals:
        events.append((start, 0))
        events.append((end, 1))
    events.sort()
    best = current = 0
    for _, kind in events:
        if kind == 0:
            current += 1
            best = max(best, current)
        else:
            current -= 1
    return best
