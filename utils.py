import logging
import sys

from datetime import timedelta


def get_weeks(start, end):
    assert start, 'No start specified'
    assert end, 'No end specified'
    dates = []
    current = (start - timedelta(days=start.weekday()))
    end = (end + timedelta(days=6-end.weekday()))
    while current < end:
        week = current + timedelta(days=7)
        dates.append((current, week))
        current = week

    return dates


log = logging.getLogger('mdm')
handler = logging.StreamHandler(sys.stderr)
log.addHandler(handler)
log.setLevel(logging.DEBUG)

logging.getLogger("requests").propagate = False
