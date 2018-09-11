import hashlib
import json
import os

from datetime import datetime, timedelta
from functools import partial
from urllib import urlencode

from utils import get_weeks, get_year, log

import requests

BUGZILLA_REST = 'https://bugzilla.mozilla.org/rest/bug?'
BUGZILLA_QUERY = 'https://bugzilla.mozilla.org/buglist.cgi?'
BUGZILLA_REQUEST = 'https://bugzilla.mozilla.org/request.cgi?'
BUGZILLA_TOKEN = os.getenv('BUGZILLA_MDM_TOKEN')

YEAR = 2018


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


def bugs_closed_component(product_component_list, **kw):
    kw = kw.copy()
    kw.update({
        'product': product_component_list[0],
        'component': product_component_list[1],
        'status': ['RESOLVED', 'VERIFIED', 'CLOSED']
    })
    return kw


def reviews_assigned(person, **kw):
    kw = kw.copy()
    kw.update({
        'status': ['UNCONFIRMED', 'ASSIGNED', 'REOPENED', 'NEW'],
        'f1': 'flagtypes.name',
        'o1': 'substring',
        'v1': 'review?',
        'f2': 'requestees.login_name',
        'o2': 'substring',
        'v2': person['bugzilla_email']
    })
    return kw


def ni_assigned_open(person, **kw):
    kw = kw.copy()
    kw.update({
        'f1': 'flagtypes.name',
        'o1': 'substring',
        'v1': 'needinfo',
        'f2': 'requestees.login_name',
        'o2': 'substring',
        'v2': person['bugzilla_email'],
        'f3': 'bug_status',
        'o3': 'regexp',
        'v3': 'UNCONFIRMED|ASSIGNED|REOPENED|NEW',
    })
    return kw


def ni_assigned(person, **kw):
    kw = kw.copy()
    kw.update({
        'f1': 'flagtypes.name',
        'o1': 'substring',
        'v1': 'needinfo',
        'f2': 'requestees.login_name',
        'o2': 'substring',
        'v2': person['bugzilla_email']
    })
    return kw


def reviews_involved(person, **kw):
    kw = kw.copy()
    kw.update({
        'f1': 'attachments.description',
        'o1': 'anywordssubstr',
        'v1': person['bugzilla_email']
    })
    return kw


def bugs_fixed_in_year(person, **kw):
    kw = kw.copy()
    timeframe = get_year(YEAR)
    kw.update({
        'emailtype1': 'substring',
        'emailassigned_to1': 1,
        'email1': person['bugzilla_email'],
        'f1': 'resolution',
        'o1': 'changedto',
        'v1': 'FIXED',
        'f2': 'resolution',
        'o2': 'changedafter',
        'v2': timeframe['start'],
        'f3': 'resolution',
        'o3': 'changedbefore',
        'v3': timeframe['end'],
    })
    return kw


def bugs_created_in_year(person, **kw):
    kw = kw.copy()
    timeregex = "^%d.*" % YEAR
    kw.update({
        'emailtype1': 'substring',
        'emailreporter1': 1,
        'email1': person['bugzilla_email'],
        'f1': 'creation_ts',
        'o1': 'regexp',
        'v1': timeregex,
    })
    if 'status' in kw:
        if kw['status'] == 'open':
            kw.update({
                'status': ['UNCONFIRMED', 'ASSIGNED', 'REOPENED', 'NEW'],
            })
    return kw


def bugs_commented_other_changed_year(person, **kw):
    kw = kw.copy()
    timeregex = "^%d.*" % YEAR
    kw.update({
        'emailtype1': 'substring',
        'emaillongdesc1': 1,
        'email1': person['bugzilla_email'],
        'f1': 'delta_ts',
        'o1': 'regexp',
        'v1': timeregex,
        'f2': 'assigned_to',
        'o2': 'notequals',
        'v2': person['bugzilla_email'],
        'f3': 'reporter',
        'o3': 'notequals',
        'v3': person['bugzilla_email'],
    })
    return kw


def as_request(person, query=None, **kw):
    query = globals().get(query)(person, **kw)
    return BUGZILLA_REQUEST + urlencode(query, True)


def as_query(person, query=None, **kw):
    query = globals().get(query)(person, **kw)
    new = {}
    translate = {'status': 'bug_status'}
    for k, v in query.items():
        new[translate.get(k, k)] = v

    return BUGZILLA_QUERY + urlencode(new, True)


def rest_query(query, cache=True):
    query.update({'api_key': BUGZILLA_TOKEN})
    query = BUGZILLA_REST + urlencode(query)

    if not cache:
        log.info('Note: not caching bugzilla query.')

    query_hash = hashlib.md5()
    query_hash.update(query)
    cache_key = 'bugzilla:' + query_hash.hexdigest()
    filename = os.path.join('cache', cache_key + '.json')

    if cache and os.path.exists(filename):
        return json.load(open(filename, 'r'))

    log.info('Bugzilla: {}'.format(query))
    result = requests.get(query).json()
    if cache:
        json.dump(result, open(filename, 'w'))

    return result


def get_query_per_week(person_or_component, query, parse=None, start=None, end=None, product=None):
    assert parse
    weeks = get_weeks(start, end)
    results = []
    for k, (start, end) in enumerate(weeks):
        if product is None:
            query_url = query(person_or_component, **parse(start, end))
        else:
            query_url = query([product, person_or_component], **parse(start, end))
        # Don't cache the last two weeks.
        cache = bool(os.getenv('FORCE_CACHE', k < (len(weeks) - 2)))
        result = rest_query(query_url, cache=cache)
        results.append((start, end, len(result['bugs'])))

    return results


def parse(week_start, week_end):
    return {
        'chfieldto': week_end.strftime('%Y-%m-%d'),
        'chfield': 'cf_last_resolved',
        'chfieldfrom': week_start.strftime('%Y-%m-%d'),
    }


def bugs_closed_per_week(person, start=None, end=None):
    return reversed(
        get_query_per_week(person, bugs_closed, parse=parse, start=start, end=end)
    )


def reviews_involved_per_week(person, start=None, end=None):
    return reversed(
        get_query_per_week(person, reviews_involved, parse=parse, start=start, end=end)
    )


def bugs_closed_by_component_per_week(product, component, start=None, end=None):
    return reversed(
        get_query_per_week(component, bugs_closed_component, parse=parse, start=start, end=end, product=product)
    )


queries = {
    # all bugs open and assigned to them
    'bugs_assigned': partial(as_query, query='bugs_assigned'),
    # all bugs with reviews requested of them
    'reviews_assigned': partial(as_query, query='reviews_assigned'),
    # all bugs with open NI on them
    'ni_assigned': partial(as_query, query='ni_assigned'),
    # all open bugs with open NI on them
    'ni_assigned_open': partial(as_query, query='ni_assigned_open'),
    # all bugs they've closed
    'closed': partial(as_query, query='bugs_closed'),
    # all fixed by them in the year
    'fixed_year': partial(as_query, query='bugs_fixed_in_year'),
    # all created by them in the year
    'created_year': partial(as_query, query='bugs_created_in_year'),
    # all created by them in the year and which are open
    'created_year_open': partial(as_query, query='bugs_created_in_year', status='open'),
    # all commented on someone else's bug and which has changed in the past year
    'commented_other_changed_year': partial(as_query, query='bugs_commented_other_changed_year'),
}
