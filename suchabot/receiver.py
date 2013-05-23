#!/usr/bin/python
import cgi
import cgitb; cgitb.enable()
import json
import os
import pipes
import subprocess

form = cgi.FieldStorage()
payload = json.loads(form['payload'])
repo = payload['repository']['full_name']
number = payload['number']

script = os.path.expanduser('~/code/SuchABot/suchabot/sync.bash')
subprocess.check_output('jsub -mem 512M {0} {1} {2}'.format(script, pipes.quote(repo), pipes.quote(number)),
                        stderr=subprocess.STDOUT, shell=True)
