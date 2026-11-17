from taskforge import issue

FAILS = {"test_x.py::test_slugify[empty]": "assert 'a' == ''"}
DETAILS = {"test_x.py::test_slugify[empty]": {"args": "text = '', expected = ''", "check": "assert slugify(text) == expected"}}
DOCS = {"test_slugify": "Slugify lowercases text"}


def test_statement_contains_inputs_and_check_but_no_fix():
    text = issue.write_issue("textkit", FAILS, DETAILS, DOCS)
    assert "text = '', expected = ''" in text
    assert "assert slugify(text) == expected" in text
    assert "case `empty`" in text


def test_leak_detection_flags_changed_lines():
    patch = "--- a/m.py\n+++ b/m.py\n@@ -1,1 +1,1 @@\n-    while i < len(a) or j < len(b):\n+    while i < len(a) and j < len(b):\n"
    assert issue.leaks("the fix is while i < len(a) and j < len(b): here", patch)
    assert not issue.leaks("intersect returns the wrong list", patch)


def test_scenarios_are_capped():
    fails = {f"test_x.py::test_a[{i}]": "assert 1 == 2" for i in range(9)}
    text = issue.write_issue("m", fails, {}, {})
    assert "and 5 more failing scenario" in text
