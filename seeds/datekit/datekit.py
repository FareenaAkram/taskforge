"""datekit: calendar arithmetic without the datetime module (Gregorian, proleptic)."""

_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def is_leap(year):
    """Gregorian leap-year rule."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year, month):
    """Number of days in the given month."""
    if not 1 <= month <= 12:
        raise ValueError("month out of range")
    if month == 2 and is_leap(year):
        return 29
    return _DAYS[month - 1]


def day_of_year(year, month, day):
    """1-based ordinal of the date within its year."""
    if not 1 <= day <= days_in_month(year, month):
        raise ValueError("day out of range")
    return sum(days_in_month(year, m) for m in range(1, month)) + day


def add_days(year, month, day, n):
    """The date n days after (or before, if n is negative) the given date."""
    day += n
    while day > days_in_month(year, month):
        day -= days_in_month(year, month)
        month += 1
        if month > 12:
            month = 1
            year += 1
    while day < 1:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        day += days_in_month(year, month)
    return (year, month, day)


def weekday(year, month, day):
    """Day of week with 0 = Monday ... 6 = Sunday (Sakamoto's algorithm)."""
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    if month < 3:
        year -= 1
    sunday_based = (year + year // 4 - year // 100 + year // 400 + t[month - 1] + day) % 7
    return (sunday_based + 6) % 7


def _ordinal(year, month, day):
    y = year - 1
    return y * 365 + y // 4 - y // 100 + y // 400 + day_of_year(year, month, day)


def days_between(d1, d2):
    """Signed number of days from d1 to d2, each a (year, month, day) tuple."""
    return _ordinal(*d2) - _ordinal(*d1)


def age_in_years(born, today):
    """Completed years between two (year, month, day) dates."""
    years = today[0] - born[0]
    if (today[1], today[2]) < (born[1], born[2]):
        years -= 1
    return years


def format_iso(year, month, day):
    """Format as YYYY-MM-DD."""
    return str(year).zfill(4) + "-" + str(month).zfill(2) + "-" + str(day).zfill(2)


def parse_iso(text):
    """Parse YYYY-MM-DD into a (year, month, day) tuple, validating the date."""
    parts = text.split("-")
    if len(parts) != 3:
        raise ValueError("expected YYYY-MM-DD")
    year, month, day = (int(p) for p in parts)
    day_of_year(year, month, day)
    return (year, month, day)
