import pytest

from taskforge.patching import PatchError, apply_patch, apply_patch_set, make_patch, split_patch

OLD = "".join(f"line {i}\n" for i in range(1, 21))


def edit(text, mapping):
    lines = text.splitlines(True)
    for n, new in mapping.items():
        lines[n - 1] = new + "\n"
    return "".join(lines)


def test_roundtrip_single_hunk():
    new = edit(OLD, {10: "changed"})
    assert apply_patch(OLD, make_patch(OLD, new, "f.py")) == new


def test_roundtrip_multiple_hunks():
    new = edit(OLD, {2: "first", 19: "last"})
    patch = make_patch(OLD, new, "f.py")
    assert patch.count("@@ ") >= 2
    assert apply_patch(OLD, patch) == new


def test_context_mismatch_is_rejected():
    patch = make_patch(OLD, edit(OLD, {10: "changed"}), "f.py")
    with pytest.raises(PatchError):
        apply_patch(edit(OLD, {9: "drifted"}), patch)


def test_empty_patch_is_identity():
    assert apply_patch(OLD, "") == OLD


def test_multi_file_patch_set():
    files = {"a.py": OLD, "b.py": OLD}
    new_a, new_b = edit(OLD, {3: "A"}), edit(OLD, {15: "B"})
    patch = make_patch(OLD, new_a, "a.py") + make_patch(OLD, new_b, "b.py")
    assert set(split_patch(patch)) == {"a.py", "b.py"}
    assert apply_patch_set(files, patch) == {"a.py": new_a, "b.py": new_b}


def test_patch_set_rejects_unknown_file():
    patch = make_patch(OLD, edit(OLD, {3: "A"}), "missing.py")
    with pytest.raises(PatchError):
        apply_patch_set({"a.py": OLD}, patch)
