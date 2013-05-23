#!/usr/bin/python
import cgi
import cgitb; cgitb.enable()
import json
import os
import pipes
import subprocess

#fix the path issues
environ = os.environ
environ['PATH'] = '/bin:/usr/bin:/usr/local/bin'

form = cgi.FieldStorage()
payload = json.loads(form['payload'])
repo = payload['repository']['full_name']
number = payload['number']

script = os.path.expanduser('~/code/SuchABot/suchabot/sync.bash')
subprocess.check_output('/usr/local/bin/jsub'
                        ' -N suchabot'
                        ' -o /data/project/suchaserver/suchabot.out'
                        ' -e /data/project/suchaserver/suchabot.err'
                        ' -mem 512M /data/project/suchaserver/code/SuchABot/suchabot/sync.bash'
                        ' {1} {2}'.format(pipes.quote(repo), pipes.quote(number)),
                        stderr=subprocess.STDOUT, shell=True, env=environ)
