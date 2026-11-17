"""textkit: small text-processing helpers."""


def slugify(text, sep="-"):
    """Lowercase, replace runs of non-alphanumerics with `sep`, strip separators."""
    out = []
    prev_sep = True
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
            prev_sep = False
        elif not prev_sep:
            out.append(sep)
            prev_sep = True
    if out and out[-1] == sep:
        out.pop()
    return "".join(out)


def truncate(text, width, ellipsis="..."):
    """Shorten text to at most `width` characters, ending with the ellipsis."""
    if width < len(ellipsis):
        raise ValueError("width too small")
    if len(text) <= width:
        return text
    return text[: width - len(ellipsis)] + ellipsis


def wrap(text, width):
    """Greedy word wrap; a word longer than width gets its own line."""
    lines = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = current + " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def count_words(text):
    """Case-insensitive word frequencies; punctuation is ignored, apostrophes kept."""
    counts = {}
    word = ""
    for ch in text.lower() + " ":
        if ch.isalpha() or ch == "'":
            word += ch
        else:
            if word:
                counts[word] = counts.get(word, 0) + 1
            word = ""
    return counts


def is_palindrome(text):
    """True if text reads the same backwards, ignoring case and non-alphanumerics."""
    letters = [c.lower() for c in text if c.isalnum()]
    i, j = 0, len(letters) - 1
    while i < j:
        if letters[i] != letters[j]:
            return False
        i += 1
        j -= 1
    return True


def caesar(text, shift):
    """Shift letters by `shift` positions, preserving case; other characters unchanged."""
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - ord("a") + shift) % 26 + ord("a")))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - ord("A") + shift) % 26 + ord("A")))
        else:
            out.append(ch)
    return "".join(out)


def rle_encode(text):
    """Run-length encode: 'aaab' -> 'a3b1'."""
    if not text:
        return ""
    out = []
    run_char, run_len = text[0], 1
    for ch in text[1:]:
        if ch == run_char:
            run_len += 1
        else:
            out.append(run_char + str(run_len))
            run_char, run_len = ch, 1
    out.append(run_char + str(run_len))
    return "".join(out)


def rle_decode(encoded):
    """Inverse of rle_encode; counts may have several digits."""
    out = []
    i = 0
    while i < len(encoded):
        ch = encoded[i]
        i += 1
        digits = ""
        while i < len(encoded) and encoded[i].isdigit():
            digits += encoded[i]
            i += 1
        out.append(ch * int(digits))
    return "".join(out)


def title_case(text, small=("a", "an", "the", "of", "and", "in", "on")):
    """Capitalise words except small words, but always the first and the last."""
    words = text.split()
    out = []
    for i, w in enumerate(words):
        if 0 < i < len(words) - 1 and w.lower() in small:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)
