import json

import os
import sys
import shutil

from datetime import datetime

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))

import bugzilla
import github

from utils import log


def clean():
    for filename in os.listdir('build'):
        if filename.startswith('.keep'):
            continue
        os.remove(os.path.join('build', filename))

    for filename in os.listdir('static'):
        shutil.copyfile(
            os.path.join('static', filename),
            os.path.join('build', filename)
        )


def load_data(filename):
    data = json.load(open(filename, 'r'))

    data['start'] = datetime.strptime(
        data.get('start', '2016-01-01'),
        '%Y-%m-%d'
        ).date()
    data['end'] = datetime.strptime(
        data.get('end', datetime.today().strftime('%Y-%m-%d')),
        '%Y-%m-%d'
        ).date()
    return data


def copy_into_build(filename, output):
    open(os.path.join('build', filename), 'w').write(output)


def merge(method, person, start=None, end=None):
    # Assume everyone has a bugzilla account.
    bugzilla_dates = getattr(bugzilla, method)(person, start=start, end=end)

    github_dates = {}
    if person['github']:
        # Annotate in the github data.
        github_dates = getattr(github, method)(person, start=start, end=end)
        github_dates = dict([(start, num) for start, _, num in github_dates])

    merged = []
    maximum = 0
    for entries in bugzilla_dates:
        total = github_dates.get(entries[0], 0) + entries[2]
        maximum = max(maximum, total)
        merged.append({
            'start': entries[0],
            'end': entries[1],
            'bugzilla': entries[2],
            'github': github_dates.get(entries[0], 0),
            'total': total
        })

    return {'merged': merged, 'max': maximum}


def generate_person(filename, template, data):
    for nick, person in data['people'].items():
        new_filename = 'person-{}.html'.format(nick)
        copy_into_build(
            new_filename,
            template.render(
                data=data,
                person=person,
                bits={
                    'bugs_closed_per_week':
                        merge(
                            'bugs_closed_per_week',
                            person,
                            start=data['start'],
                            end=data['end']
                        ),
                    'reviews_involved_per_week':
                        merge(
                            'reviews_involved_per_week',
                            person,
                            start=data['start'],
                            end=data['end']
                        )
                }
            )
        )



def generate_index(filename, template, data):
    people = sorted((k, v) for k, v in data['people'].items())
    copy_into_build(
        filename,
        template.render(
            data=data, people=people,
            bugzilla_queries=bugzilla.queries
        )
    )


def generate_templates(data):
    for filename in os.listdir('templates'):
        if filename == 'layout.html':
            continue

        name = os.path.splitext(filename)[0]
        method = globals().get('generate_' + name)
        if not method:
            print ('No method: generate_{} found for file: {}'
                   .format(name, filename))
        else:
            method(filename, env.get_template(filename), data)


if __name__=='__main__':
    clean()
    data = load_data(sys.argv[1])
    generate_templates(data)
