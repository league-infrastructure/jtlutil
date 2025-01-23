from datetime import datetime, timedelta
from src.jtlutil.datecalc import start_of_today, start_of_yesterday
from src.jtlutil.datecalc import end_of_today


def test_start_of_today():
    result = start_of_today()
    now = datetime.now()
    expected = datetime(now.year, now.month, now.day)
    assert result == expected, f"Expected {expected}, but got {result}"

def test_start_of_yesterday():
    result = start_of_yesterday()
    now = datetime.now()
    expected = datetime(now.year, now.month, now.day) - timedelta(days=1)
    assert result == expected, f"Expected {expected}, but got {result}"

def test_end_of_today():
    result = end_of_today()
    now = datetime.now()
    expected = datetime(now.year, now.month, now.day) + timedelta(days=1, seconds=-1)
    assert result == expected, f"Expected {expected}, but got {result}"
