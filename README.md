Useful pages and queries relating to addons at mozilla.

Installation
------------

`pip install -r requirements.txt`

Configuration
-------------

Create a .json file containing information about the team, see `addons.json`
as a template.

To authenticate against Github and prevent hitting API limits, you'll need
to provide an API key and token as environment variables:

`export GITHUB_USERNAME=your-username`
`export GITHUB_TOKEN=your-token`

Generation
----------

`python generate.py your-team-file.json`

This can take a while as it has to run through lots of queries. Will generate
output into the `build` directory.

By default all queries to bugzilla and github are cached apart from the last
two weeks so that if you run it mid week, you'll catch the entries for that
week later. For fast re-generation the `FORCE_CACHE` environment variable:

`export FORCE_CACHE=true`

To go back to normal caching:

`unset FORCE_CACHE`
