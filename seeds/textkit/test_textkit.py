import pytest

from textkit import (caesar, count_words, is_palindrome, rle_decode, rle_encode,
                     slugify, title_case, truncate, wrap)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Hello, World!", "hello-world"),
        ("  spaces   everywhere ", "spaces-everywhere"),
        ("Already-slugged", "already-slugged"),
        ("", ""),
        ("!!!", ""),
        ("a_b c", "a-b-c"),
        ("Route 66", "route-66"),
    ],
    ids=["punct", "spaces", "hyphen", "empty", "symbols", "underscore", "digits"],
)
def test_slugify(text, expected):
    """Slugify lowercases text and joins words with hyphens"""
    assert slugify(text) == expected


def test_slugify_custom_separator():
    """Slugify honours a custom separator, including multi-character ones"""
    assert slugify("A B C", sep="_") == "a_b_c"
    assert slugify("x!!", sep="_") == "x"
    assert slugify("a  b", sep="--") == "a--b"


def test_truncate_short_text_unchanged():
    """Text that already fits is returned unchanged"""
    assert truncate("hello", 5) == "hello"
    assert truncate("hello", 10) == "hello"


def test_truncate_long_text():
    """Long text is cut so the result, ellipsis included, fits the width"""
    assert truncate("hello world", 8) == "hello..."
    assert truncate("abcdefgh", 7) == "abcd..."
    assert truncate("abcdefgh", 5, "~") == "abcd~"


def test_truncate_width_validation():
    """A width smaller than the ellipsis is rejected"""
    with pytest.raises(ValueError):
        truncate("abcdef", 2)
    assert truncate("abcdef", 3) == "..."


def test_wrap_basic():
    """Wrap fills lines greedily up to the width"""
    assert wrap("the quick brown fox", 9) == ["the quick", "brown fox"]


def test_wrap_width_boundary():
    """A line may be exactly as wide as the limit but no wider"""
    assert wrap("aa bb", 5) == ["aa bb"]
    assert wrap("aa bb", 4) == ["aa", "bb"]


def test_wrap_long_word():
    """A word longer than the width sits on its own line"""
    assert wrap("supercalifragilistic is long", 10) == ["supercalifragilistic", "is long"]


def test_wrap_empty_input():
    """Empty or blank input produces no lines"""
    assert wrap("", 10) == []
    assert wrap("   ", 5) == []


def test_count_words_basic():
    """Word counts ignore case"""
    assert count_words("The cat and the hat") == {"the": 2, "cat": 1, "and": 1, "hat": 1}


def test_count_words_punctuation():
    """Punctuation separates words and is not counted"""
    assert count_words("Hi, hi! HI?") == {"hi": 3}
    assert count_words("one two") == {"one": 1, "two": 1}


def test_count_words_apostrophes_and_empty():
    """Apostrophes stay inside words and empty text has no words"""
    assert count_words("don't stop") == {"don't": 1, "stop": 1}
    assert count_words("") == {}
    assert count_words("  ...  ") == {}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("racecar", True),
        ("A man, a plan, a canal: Panama", True),
        ("hello", False),
        ("", True),
        ("ab", False),
        ("Aa", True),
        ("abcba", True),
        ("abccba", True),
        ("abcdba", False),
        ("12321", True),
        ("12345", False),
    ],
    ids=["racecar", "sentence", "hello", "empty", "ab", "case", "odd", "even", "middle", "digits", "digits_no"],
)
def test_is_palindrome(text, expected):
    """Palindromes are detected ignoring case and punctuation"""
    assert is_palindrome(text) is expected


@pytest.mark.parametrize(
    "text,shift,expected",
    [
        ("abc", 1, "bcd"),
        ("xyz", 3, "abc"),
        ("Hello, World!", 13, "Uryyb, Jbeyq!"),
        ("abc", -1, "zab"),
        ("ABC", 27, "BCD"),
        ("a1 b2", 0, "a1 b2"),
        ("XYZ", 3, "ABC"),
        ("Zz", 1, "Aa"),
    ],
    ids=["simple", "wrap", "rot13", "negative", "big", "noop", "upper_wrap", "mixed"],
)
def test_caesar(text, shift, expected):
    """Caesar shifts letters and leaves everything else alone"""
    assert caesar(text, shift) == expected


def test_caesar_roundtrip():
    """Shifting forward then back restores the text"""
    s = "Attack at Dawn, 5pm!"
    assert caesar(caesar(s, 5), -5) == s


@pytest.mark.parametrize(
    "text,expected",
    [("", ""), ("aaab", "a3b1"), ("abc", "a1b1c1"), ("a" * 12, "a12"), ("aabb", "a2b2"), ("z", "z1")],
    ids=["empty", "basic", "singles", "long_run", "pairs", "one"],
)
def test_rle_encode(text, expected):
    """Run-length encoding writes each character followed by its run length"""
    assert rle_encode(text) == expected


@pytest.mark.parametrize(
    "encoded,expected",
    [("", ""), ("a3b1", "aaab"), ("a12", "a" * 12), ("x1y2", "xyy")],
    ids=["empty", "basic", "multi_digit", "mixed"],
)
def test_rle_decode(encoded, expected):
    """Run-length decoding expands counts, including multi-digit counts"""
    assert rle_decode(encoded) == expected


def test_rle_roundtrip():
    """Decoding an encoded string restores it"""
    for s in ["aaabccdddd", "abc", "zzzzzzzzzzzzzzzz", "q"]:
        assert rle_decode(rle_encode(s)) == s


def test_title_case_small_words():
    """Small words stay lowercase in the middle of a title"""
    assert title_case("the lord of the rings") == "The Lord of the Rings"
    assert title_case("war and peace") == "War and Peace"
    assert title_case("a tale of two cities") == "A Tale of Two Cities"


def test_title_case_first_and_last_always_capitalised():
    """The first and last word are capitalised even when they are small words"""
    assert title_case("what is it in") == "What Is It In"
    assert title_case("war and") == "War And"


def test_title_case_normalises_case():
    """Remaining letters of each word are lowercased"""
    assert title_case("hELLO wORLD") == "Hello World"
    assert title_case("hello") == "Hello"
    assert title_case("") == ""


def test_title_case_custom_small_words():
    """The list of small words can be overridden"""
    assert title_case("go to town", small=("to",)) == "Go to Town"
