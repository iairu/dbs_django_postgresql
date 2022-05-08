from datetime import datetime
from calendar import timegm


def datetime_unix(_datetime: datetime):
    return timegm(_datetime.timetuple())