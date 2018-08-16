import os
import requests
import time

from utils import log


BASE_URL = 'https://bugzilla.mozilla.org'
URL = '{}/rest/bug'.format(BASE_URL)
BUGZILLA_TOKEN = os.getenv('BUGZILLA_MDM_TOKEN')

BUG_CACHE = {}


def authd_request(url, params):
    params['api_key'] = BUGZILLA_TOKEN
    return requests.get(url, params=params)


def get_overall_blockers(data):
    start = time.time()
#    components = [v[1] for v in data['bugzilla']['components']]
    params = {
        'f1': 'blocked',
        'o1': 'isnotempty',
        'include_fields': 'blocks,id,summary',
        'status': ['UNCONFIRMED', 'NEW', 'ASSIGNED', 'REOPENED'],
#        'component': components
    }
    # startval is the field|order|value index already used in param above
    params.update(get_product_components(data, 1))
    res = authd_request(URL, params=params)
    res.raise_for_status()
    log.debug('Getting overall blockers took: {}'.format(time.time() - start))
    return res.json()['bugs']


def get_product_components(data, startval):
    params = {
        'j_top': 'OR'
    }
    counter = startval
    params_template = [
        ['f', 'OP'],
        ['f', 'product', 'o', 'equals', 'v'],
        ['f', 'component', 'o', 'equals', 'v'],
        ['f', 'CP']
    ]
    for product_component in data['bugzilla']['components']:
        for group in params_template:
            counter += 1
            params[group[0] + str(counter)] = group[1]
            if len(group) > 2:
                params[group[0] + str(counter)] = group[1]
                params[group[2] + str(counter)] = group[3]
                if group[1] == "product":
                    params[group[4] + str(counter)] = product_component[0]
                if group[1] == "component":
                    params[group[4] + str(counter)] = product_component[1]
    return params


def get_one_bug(id):
    if id in BUG_CACHE:
        return BUG_CACHE[id]

    url = URL + '/%s' % id
    params = {
        'include_fields': 'id,status,resolution,blocks'
    }

    res = authd_request(url, params=params)
    if res.status_code in (400, 401):
        log.warning(
            'Failed to get bug {} response {}'.format(id, res.status_code))
        return None

    res.raise_for_status()
    BUG_CACHE[id] = res.json()['bugs'][0]
    return BUG_CACHE[id]


def recurse_blockers(bug):
    recurse = {}
    log.debug('Recursing down for bug: {}'.format(bug['id']))

    def lookup_bugs(lookup):
        for bug in lookup['blocks']:
            blocker = get_one_bug(bug)
            if blocker:
                recurse[blocker['id']] = blocker
                lookup_bugs(blocker)

    lookup_bugs(bug)
    return recurse


def collect(data):
    if not data['bugzilla']['components']:
        return []

    blocks = {}
    for bug in get_overall_blockers(data):
        if len(bug['blocks']) > 2:
            bugs = recurse_blockers(bug)
            data = {
                'open': [],
                'closed': [],
                'total': 0,
                'id': bug['id'],
                'summary': bug['summary']
            }
            for blockers_bug_id, blockers_bug in bugs.items():
                if blockers_bug['status'] in ['RESOLVED']:
                    data['closed'].append(blockers_bug)
                else:
                    data['open'].append(blockers_bug)
                data['total'] += 1

            blocks[bug['id']] = data

    bugs = sorted([(v['total'], v) for k, v in blocks.items()])
    return list(reversed([v for _, v in bugs]))
