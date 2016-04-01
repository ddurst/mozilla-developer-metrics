import hashlib
import json
import os

from datetime import datetime, timedelta
from functools import partial
from urllib import urlencode

import requests

bugzilla_rest = 'https://bugzilla.mozilla.org/rest/bug?'
bugzilla_query = 'https://bugzilla.mozilla.org/buglist.cgi?'


def bugs_assigned(person, **kw):
    kw = kw.copy()
    kw.update({
        'emailtype1': 'exact',
        'emailassigned_to1': '1',
        'email1': person['bugzilla_email'],
        'status': ['UNCONFIRMED', 'ASSIGNED', 'REOPENED', 'NEW']
    })
    return kw


def bugs_closed(person, **kw):
    kw = kw.copy()
    kw.update({
        'emailtype1': 'exact',
        'emailassigned_to1': '1',
        'email1': person['bugzilla_email'],
        'status': ['RESOLVED', 'VERIFIED', 'CLOSED']
    })
    return kw


def reviews_assigned(person, **kw):
    kw = kw.copy()
    kw.update({
        'f1': 'attachments.description',
        'o1': 'anywords',
        'resolution': '---',
        'v1': 'r?' + person['bugzilla_nick']
    })
    return kw


def as_query(person, query=None, **kw):
    query = globals().get(query)(person, **kw)
    new = {}
    translate = {'status': 'bug_status'}
    for k, v in query.items():
        new[translate.get(k, k)] = v

    return bugzilla_query + urlencode(new, True)


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


def rest_query(query):
    query = bugzilla_rest + urlencode(query)
    query_hash = hashlib.md5()
    query_hash.update(query)
    cache_key = query_hash.hexdigest()
    filename = os.path.join('cache', cache_key + '.json')

    if os.path.exists(filename):
        return json.load(open(filename, 'r'))

    result = requests.get(query).json()
    json.dump(result, open(filename, 'w'))
    return result


def get_query_per_week(person, parse=None, start=None, end=None):
    weeks = get_weeks(start, end)
    results = []
    for start, end in weeks:
        query = bugs_closed(person, **parse(start, end))
        result = rest_query(query)
        results.append((start, end, len(result['bugs'])))

    return results


def bugs_closed_per_week(person, start=None, end=None):
    def parse(week_start, week_end):
        return {
            'chfieldto': week_end.strftime('%Y-%m-%d'),
            'chfield': 'cf_last_resolved',
            'chfieldfrom': week_start.strftime('%Y-%m-%d'),
        }

    return reversed(
        get_query_per_week(person, parse=parse, start=start, end=end)
    )


queries = {
    'bugs_assigned': partial(as_query, query='bugs_assigned'),
    'closed': partial(as_query, query='bugs_closed'),
    'reviews_assigned': partial(as_query, query='reviews_assigned')
}
