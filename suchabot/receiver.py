#!/usr/bin/python
import cgi
import cgitb
import json
import os
import pipes
import subprocess
import logging

cgitb.enable()

#fix the path issues
environ = os.environ
environ['PATH'] = '/bin:/usr/bin:/usr/local/bin'

form = cgi.FieldStorage()
payload = json.loads(form['payload'].value)
repo = payload['repository']['name']
number = str(payload['number'])
action = payload['action']

logging.basicConfig(format='%%(asctime)s %s PR#%s %s %%(message)s' % (repo, number, action), filename=os.path.expanduser('~/logs/%s.receive' % repo), level=logging.INFO)

logging.info('received')
output = subprocess.check_output('/usr/local/bin/jsub'
                                ' -N suchabot'
                                ' -o /data/project/suchaserver/suchabot.out'
                                ' -e /data/project/suchaserver/suchabot.err'
                                ' -mem 512M /data/project/suchaserver/code/SuchABot/suchabot/sync.bash'
                                ' {0} {1}'.format(pipes.quote(repo), pipes.quote(number)),
                                stderr=subprocess.STDOUT, shell=True, env=environ)

# Sortof potentially hopefully stable way to get the job id.
# valhallasw says it should be okay....
jobid = output.split('\n')[1].split(' ')[2]

logging.info("queued job %s", jobid)
