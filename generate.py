import json
import os
import sys
import shutil

from datetime import datetime

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))

from bugzilla import bugs_closed_per_week, queries as bugzilla_queries


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


def generate_person(filename, template, data):
    for nick, person in data['people'].items():
        new_filename = 'person-{}.html'.format(nick)
        bugzilla_bugs = {
            'bugs_closed_per_week': bugs_closed_per_week(
                person,
                start=data['start'],
                end=data['end']
            )
        }
        copy_into_build(
            new_filename,
            template.render(
                data=data,
                person=person,
                bugzilla_bugs=bugzilla_bugs
            )
        )


def generate_index(filename, template, data):
    people = sorted((k, v) for k, v in data['people'].items())
    copy_into_build(
        filename,
        template.render(
            data=data, people=people, bugzilla_queries=bugzilla_queries
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
    data = load_data('addons.json')
    generate_templates(data)
