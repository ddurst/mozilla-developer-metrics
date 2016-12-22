import hashlib
import json
import os
import time

from datetime import datetime, timedelta
from functools import partial
from urllib import quote
from urllib import urlencode

from utils import get_weeks, log

import requests

github_rest = 'https://api.github.com/search/issues?q='
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')


def rest_query(query, cache=True):
    query = github_rest + '+'.join(query)

    if not cache:
        log.info('Note: not caching github query')

    query_hash = hashlib.md5()
    query_hash.update(query)
    cache_key = 'github:' + query_hash.hexdigest()
    filename = os.path.join('cache', cache_key + '.json')

    if cache and os.path.exists(filename):
        return json.load(open(filename, 'r'))

    log.info('Github: {}'.format(query))
    result = requests.get(query, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
    result.raise_for_status()
    time.sleep(1)
    result_json = result.json()

    if cache:
        json.dump(result_json, open(filename, 'w'))
    return result_json


def bugs_closed(person, *args):
    args = args[:]
    args += (
        'type:issue',
        'state:closed',
        'assignee:{}'.format(person['github']),
    )
    return args


def reviews_involved(person, *args):
    args = args[:]
    args += (
        'type:pr',
        'state:closed',
        'involves:{}'.format(person['github']),
    )
    return args


def get_query_per_week(person, query, parse=None, start=None, end=None):
    assert parse
    weeks = get_weeks(start, end)
    results = []
    for k, (start, end) in enumerate(weeks):
        query_url = query(person, *parse(start, end))
        # Don't cache the last two weeks.
        cache = bool(os.getenv('FORCE_CACHE', k < (len(weeks) - 2)))
        result = rest_query(query_url, cache=cache)
        results.append((start, end, result['total_count']))

    return results


def parse(week_start, week_end):
    return {
        'closed:"{} .. {}"'.format(
            week_start.strftime('%Y-%m-%d'),
            week_end.strftime('%Y-%m-%d')
        )
    }


def bugs_closed_per_week(person, start=None, end=None):
    return get_query_per_week(
        person, bugs_closed, parse=parse, start=start, end=end
    )


def reviews_involved_per_week(person, start=None, end=None):
    return get_query_per_week(
        person, reviews_involved, parse=parse, start=start, end=end
    )
