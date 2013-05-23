import cgi
import json
import pipes
import subprocess

form = cgi.FieldStorage()
payload = json.loads(form['payload'])
repo = payload['repository']['full_name']
number = payload['number']

subprocess.check_output('jsub -mem 512M ~/code/SuchABot/suchabot/sync.bash ' + pipes.quote(repo) + ' '+ pipes.quote(number),
                        stderr=subprocess.STDOUT, shell=True)
