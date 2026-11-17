import datetime as dt

import pytest

from datekit import (add_days, age_in_years, day_of_year, days_between, days_in_month,
                     format_iso, is_leap, parse_iso, weekday)


@pytest.mark.parametrize(
    "year,expected",
    [(2000, True), (1900, False), (2024, True), (2023, False), (2100, False), (1600, True), (4, True), (100, False)],
)
def test_is_leap(year, expected):
    """Leap years are divisible by 4, except centuries not divisible by 400"""
    assert is_leap(year) is expected


def test_days_in_month_regular_year():
    """Month lengths in a non-leap year"""
    assert [days_in_month(2023, m) for m in range(1, 13)] == [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def test_days_in_month_february():
    """February has 29 days only in leap years"""
    assert days_in_month(2024, 2) == 29
    assert days_in_month(1900, 2) == 28
    assert days_in_month(2000, 2) == 29


def test_days_in_month_rejects_bad_month():
    """Months outside 1-12 are rejected"""
    with pytest.raises(ValueError):
        days_in_month(2024, 0)
    with pytest.raises(ValueError):
        days_in_month(2024, 13)


@pytest.mark.parametrize(
    "date,expected",
    [
        ((2023, 1, 1), 1),
        ((2023, 12, 31), 365),
        ((2024, 12, 31), 366),
        ((2024, 3, 1), 61),
        ((2023, 3, 1), 60),
        ((2023, 2, 28), 59),
        ((2024, 2, 29), 60),
        ((2023, 1, 31), 31),
        ((2023, 2, 1), 32),
    ],
)
def test_day_of_year(date, expected):
    """Day-of-year counts from 1 on January 1st"""
    assert day_of_year(*date) == expected


@pytest.mark.parametrize("date", [(2023, 2, 29), (2023, 4, 31), (2023, 1, 0), (2023, 13, 1)])
def test_day_of_year_rejects_invalid_dates(date):
    """Impossible dates are rejected"""
    with pytest.raises(ValueError):
        day_of_year(*date)


@pytest.mark.parametrize(
    "args,expected",
    [
        ((2023, 1, 31, 1), (2023, 2, 1)),
        ((2023, 12, 31, 1), (2024, 1, 1)),
        ((2024, 2, 28, 1), (2024, 2, 29)),
        ((2023, 2, 28, 1), (2023, 3, 1)),
        ((2023, 3, 1, -1), (2023, 2, 28)),
        ((2024, 1, 1, -1), (2023, 12, 31)),
        ((2023, 1, 1, 0), (2023, 1, 1)),
        ((2023, 1, 1, 365), (2024, 1, 1)),
        ((2024, 1, 1, 366), (2025, 1, 1)),
        ((2023, 1, 15, -15), (2022, 12, 31)),
        ((2024, 3, 1, -1), (2024, 2, 29)),
    ],
)
def test_add_days_examples(args, expected):
    """Adding days rolls over months and years in both directions"""
    assert add_days(*args) == expected


@pytest.mark.parametrize("n", [-800, -400, -31, -1, 0, 1, 30, 31, 59, 60, 365, 366, 1461, 3000])
def test_add_days_matches_datetime(n):
    """add_days agrees with the standard library"""
    expected = dt.date(2000, 1, 31) + dt.timedelta(days=n)
    assert add_days(2000, 1, 31, n) == (expected.year, expected.month, expected.day)


@pytest.mark.parametrize(
    "date",
    [(2024, 1, 1), (2024, 2, 29), (2023, 3, 1), (2000, 12, 31), (1999, 1, 31), (2024, 7, 4), (1970, 1, 1), (2021, 2, 28), (2100, 3, 1)],
)
def test_weekday_matches_datetime(date):
    """Weekday uses 0 = Monday and agrees with the standard library"""
    assert weekday(*date) == dt.date(*date).weekday()


def test_weekday_known_dates():
    """A few well-known dates"""
    assert weekday(2024, 1, 1) == 0
    assert weekday(2000, 1, 1) == 5
    assert weekday(2023, 12, 31) == 6


@pytest.mark.parametrize(
    "d1,d2",
    [
        ((2023, 1, 1), (2024, 1, 1)),
        ((2024, 1, 1), (2023, 1, 1)),
        ((2024, 2, 28), (2024, 3, 1)),
        ((2000, 1, 1), (2000, 1, 1)),
        ((1999, 12, 31), (2001, 1, 1)),
        ((2100, 2, 28), (2100, 3, 1)),
    ],
)
def test_days_between_matches_datetime(d1, d2):
    """Day differences are signed and agree with the standard library"""
    assert days_between(d1, d2) == (dt.date(*d2) - dt.date(*d1)).days


@pytest.mark.parametrize(
    "born,today,expected",
    [
        ((2000, 5, 17), (2024, 5, 17), 24),
        ((2000, 5, 17), (2024, 5, 16), 23),
        ((2000, 5, 17), (2024, 4, 30), 23),
        ((2000, 5, 17), (2024, 6, 1), 24),
        ((2000, 5, 17), (2000, 12, 1), 0),
        ((2000, 2, 29), (2023, 2, 28), 22),
        ((2000, 2, 29), (2023, 3, 1), 23),
        ((2000, 5, 17), (2024, 5, 18), 24),
    ],
)
def test_age_in_years(born, today, expected):
    """Age counts completed years, so birthdays matter"""
    assert age_in_years(born, today) == expected


def test_format_iso_pads_fields():
    """ISO formatting zero-pads year, month and day"""
    assert format_iso(2024, 3, 5) == "2024-03-05"
    assert format_iso(5, 1, 1) == "0005-01-01"
    assert format_iso(2024, 12, 31) == "2024-12-31"


def test_parse_iso_valid():
    """Valid ISO dates parse to tuples"""
    assert parse_iso("2024-03-05") == (2024, 3, 5)
    assert parse_iso("2024-3-5") == (2024, 3, 5)


@pytest.mark.parametrize("text", ["2023-02-29", "2024-03", "2024-03-05-01", "abc", "2024-13-01", "2024-00-10"])
def test_parse_iso_invalid(text):
    """Malformed or impossible dates are rejected"""
    with pytest.raises(ValueError):
        parse_iso(text)


def test_iso_roundtrip():
    """Formatting then parsing restores the date"""
    for date in [(2024, 2, 29), (1999, 12, 31), (2000, 1, 1)]:
        assert parse_iso(format_iso(*date)) == date
