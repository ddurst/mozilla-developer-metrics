import csv
from datetime import datetime
import json
import requests
import StringIO
import sys
from urllib import urlencode
import hashlib
import os

from utils import log


def get_csv(person, component, cache=False):
    # This probably does not make sense to cache.
    url = 'https://bugzilla.mozilla.org/request.cgi?'
    args = {
        'action': 'queue',
        'component': component,
        'do_union': 0,
        'group': 'type',
        'requestee': person,
        'type': 'all',
        'ctype': 'csv'
    }
    query = url + urlencode(args)
    query_hash = hashlib.md5()
    query_hash.update(query)
    cache_key = 'bugzilla:' + query_hash.hexdigest()
    filename = os.path.join('cache', cache_key + '.csv')

    data = None
    if cache and os.path.exists(filename):
        log.info('Reading from: {}'.format(filename))
        data = open(filename, 'r')

    if not data:
        log.info('Bugzilla: {}'.format(query))
        res = requests.get(query)
        res.raise_for_status()
        data = StringIO.StringIO()
        data.write(res.content)
        data.seek(0)
        if cache:
            open(filename, 'w').write(res.content)

    # Because Bugzilla is stupid.
    if data == 'No requests.':
        return []

    reader = csv.DictReader(data)
    return reader


def collect(data):
    results = {}
    for nick, person in data['people'].items():
        for component, short in data['bugzilla']['components']:
            result = get_csv(person['bugzilla_email'], component, True)
            for row in result:
                if row['Flag'] == 'review':
                    row['Created'] = datetime.strptime(
                        row['Created'], '%Y-%m-%d %H:%M %Z').date()
                    results[row['Bug ID']] = row

    results = sorted([r['Created'], r] for r in results.values())
    results = [r[1] for r in results]
    return results
