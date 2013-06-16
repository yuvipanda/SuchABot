import os
import logging
import json

import github
import redis
import yaml
import jinja2

ABANDON_TEMPLATE = jinja2.Template("""Change abandoned by {{event.abandoner.name}}
Reason:
{{event.reason}}""")

MERGE_TEMPLATE = jinja2.Template("""Change merged by {{event.submitter.name}}
Reason:
{{event.reason}}""")

RESTORE_TEMPLATE = jinja2.Template("""Change merged by {{event.restorer.name}}
Reason:
{{event.reason}}""")

COMMENT_TEMPLATE = jinja2.Template("""{{event.author.name}} left a comment on Gerrit:

{{event.comment}}""")

CONFIG_FILE = os.path.expanduser('~/.suchabot.yaml')
with open(CONFIG_FILE) as f:
    config = yaml.load(f)

OWNER = config['github']['owner']
WORKING_DIR = os.path.expanduser('~/.sucharepos')

REDIS_DB = config['redis']['db']
REDIS_HOST = config['redis']['host']
PREFIX = config['sync']['github']['redis_prefix']
CLIENT_KEY = PREFIX # We use the same thing for now

logging.basicConfig(format='%(asctime)s %(message)s', filename=os.path.expanduser('~/logs/github-sync'), level=logging.INFO)

gh = github.GitHub(username=config['github']['username'], password=config['github']['password'])

logging.info('Attempting to Redis connection to %s', REDIS_HOST)
red = redis.StrictRedis(host=REDIS_HOST, db=REDIS_DB)
logging.info('Redis connection to %s succeded', REDIS_HOST)

def make_key(*key_parts):
    return PREFIX + "_" + '.'.join(key_parts)

def change_abandoned(gerrit_data, gh_name, pr_num):
    gh.repos(OWNER, gh_name).issues(pr_num).comments.post(body=ABANDON_TEMPLATE.render(event=gerrit_data))
    logging.info("Left comment about abandonment on %s/%s", gh_name, pr_num)
    gh.repos(OWNER, gh_name).issues(pr_num).post(state='closed')
    logging.info("Closed Pull Request %s/%s", gh_name, pr_num)

def change_merged(gerrit_data, gh_name, pr_num):
    gh.repos(OWNER, gh_name).issues(pr_num).comments.post(body=MERGE_TEMPLATE.render(event=gerrit_data))
    logging.info("Left comment about merging on %s/%s", gh_name, pr_num)
    gh.repos(OWNER, gh_name).issues(pr_num).post(state='closed')
    logging.info("Closed Pull Request %s/%s", gh_name, pr_num)

def change_restored(gerrit_data, gh_name, pr_num):
    gh.repos(OWNER, gh_name).issues(pr_num).comments.post(body=RESTORE_TEMPLATE.render(event=gerrit_data))
    logging.info("Left comment about re-opening on %s/%s", gh_name, pr_num)
    gh.repos(OWNER, gh_name).issues(pr_num).post(state='open')
    logging.info("Reopened Pull Request %s/%s", gh_name, pr_num)

def comment_added(gerrit_data, gh_name, pr_num):
    gh.repos(OWNER, gh_name).issues(pr_num).comments.post(body=COMMENT_TEMPLATE.render(event=gerrit_data))
    logging.info("Left comment about comment on %s/%s", gh_name, pr_num)

type_responses = {
        'change-abandoned': change_abandoned,
        'change-merged': change_merged,
        'comment-added': comment_added,
        'change-restored': change_restored
}

if __name__ == '__main__':
    while True:
        data = json.loads(red.brpop(CLIENT_KEY)[1])
        # FIXME: Needs to be far more robust
        if 'change' not in data or not data['change']['topic'].startswith('github/pr'):
            continue
        gh_name = data['change']['project'].replace('/', '-')
        pr_num = int(data['change']['topic'].split('/')[-1])
        if data['type'] in type_responses:
            type_responses[data['type']](data, gh_name, pr_num)
