
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

def start_of_today():
    """Return the start of today as a string in isoformat in the Z timezone"""
   

    # Get current time
    now = datetime.now()

    # Get start of the day
    return datetime(now.year, now.month, now.day)

def start_of_yesterday():
    """Return the start of yesterday """
    

    # Get current time
    now = datetime.now()

    # Get start of yesterday
    return datetime(now.year, now.month, now.day) + timedelta(days=-1)


def start_of_tomorrow():
    """Return the start of tomorrow """
    

    # Get current time
    now = datetime.now()

    # Get start of tomorrow
    return datetime(now.year, now.month, now.day) + timedelta(days=1)

def end_of_today():
    """Return the end of today as a string in isoformat in the Z timezone"""
   

    # Get current time
    now = datetime.now()

    # Get end of the day
    return datetime(now.year, now.month, now.day) + timedelta(days=1, seconds=-1)

def end_of_yesterday():
    """Return the end of yesterday """
    

    # Get current time
    now = datetime.now()

    # Get end of yesterday
    return datetime(now.year, now.month, now.day) + timedelta(seconds=-1)

def start_of_day(dt: datetime):
    """Return the start of the day for the given datetime"""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def start_of_next_day(dt: datetime):
    """Return the start of the next day for the given datetime"""
    return start_of_day(dt) + timedelta(days=1)





def one_month_ago():
    return (datetime.now() - relativedelta(months=1)) \
        .replace(hour=0, minute=0, second=0, microsecond=0)


def one_month_before(dt: datetime):
    return (dt - relativedelta(months=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def one_month_after(dt: datetime):
    return (dt + relativedelta(months=1)).replace(hour=23, minute=59, second=59, microsecond=0)

def add_months(dt: datetime, months: int):
    return (dt + relativedelta(months=months))

def month_range(start_date, end_date):
    """Generate Month ranges from the start date to the end date """
    while start_date <= end_date:
        yield start_date.replace(hour=0, minute=0, second=0, microsecond=0), \
            start_date + relativedelta(months=1)
        start_date += relativedelta(months=1)


def convert_naive(dt: datetime):
    """Convert a naive datetime to a timezone aware datetime, but only if it is naive"""

    if dt.tzinfo is None:
        from pytz import utc
        return utc.localize(dt)
    else:
        return dt

