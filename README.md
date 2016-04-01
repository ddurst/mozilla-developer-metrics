Useful pages and queries relating to addons at mozilla.

Installation
------------

`pip install -r requirements.txt`

Configuration
-------------

Create a .json file containing information about the team, see `addons.json`
as a template.

Generation
----------

`python generate.py [team.json]`

This can take a while as it has to run through lots of queries. Will generate
output into the `build` directory.
