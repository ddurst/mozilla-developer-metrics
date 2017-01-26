import json
import logging
import sys

import datetime as datetime_base
from datetime import datetime, timedelta


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime_base.date):
            return datetime.strftime(obj, '%Y-%m-%d')

        return json.JSONEncoder.default(self, obj)


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
