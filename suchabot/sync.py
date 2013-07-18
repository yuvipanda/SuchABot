import os
import sys
import logging

import github
import sh
import jinja2
import yaml
import re


WORKING_DIR = os.path.expanduser("~/.sucharepos")
CONFIG_PATH = os.path.expanduser('~/.suchabot.yaml')
REPOS_MAPPING = yaml.load(open('repos.yaml'))
REPOS_GITHUB_TO_GERRIT = REPOS_MAPPING['repos']
REPOS_GERRIT_TO_GITHUB = {v:k for k, v in REPOS_GITHUB_TO_GERRIT.iteritems()}
OWNER = "wikimedia"
CHANGE_ID_REGEX = re.compile('Change-Id: (\w+)')
GERRIT_TAG_REGEX = re.compile('^(Bug|RT):', re.MULTILINE | re.IGNORECASE)
GERRIT_TEMPLATE = "ssh://suchabot@gerrit.wikimedia.org:29418/%s.git"
BOT_AUTHOR = "SuchABot <yuvipanda+suchabot@gmail.com>"
COMMIT_MSG_TEMPLATE = jinja2.Template("""{{pr.title}}

{{body}}
GitHub: {{pr.html_url}}
{% if change_id %}Change-Id: {{change_id}} {% endif %}""")

with open(CONFIG_PATH) as f:
    config = yaml.load(f)
gh = github.GitHub(username=config['github']['username'], password=config['github']['password'])


def is_git_repo(path):
    return os.path.exists(path) and os.path.exists(os.path.join(path, '.git'))


def path_for_name(name):
    return os.path.join(WORKING_DIR, name.replace('/', '-'))


def gerrit_name_for(gh_name):
    if gh_name in REPOS_GITHUB_TO_GERRIT:
        return REPOS_GITHUB_TO_GERRIT[gh_name]
    return gh_name.replace('-', '/')

def ensure_repo(name):
    if not os.path.exists(WORKING_DIR):
        sh.mkdir('-p', WORKING_DIR)
        logging.info('working directory %s created' % WORKING_DIR)
    fs_name = name.replace('/', '-')
    clone_folder = os.path.join(WORKING_DIR, fs_name)
    if is_git_repo(clone_folder):
        sh.cd(clone_folder)
        logging.info("Found Repo. Updating")
        sh.git.fetch('origin')
        sh.git.fetch('gerrit')
        logging.info("Repo updated")
    else:
        logging.info("Repo not found. Cloning")
        sh.cd(WORKING_DIR)
        sh.git.clone(GERRIT_TEMPLATE % name, fs_name)
        logging.info("Clone completed. Setting up git review")
        sh.cd(fs_name)
        sh.git.remote('add', 'gerrit', GERRIT_TEMPLATE % name)
        sh.git.review('-s')
        logging.info("git review setup")


def get_pullreq(name, number):
    gh_name = name.replace('/', '-')
    pr = gh.repos(OWNER, gh_name).pulls(number).get()
    return pr


def gerrit_url_for(change_id):
    return "https://gerrit.wikimedia.org/r/#q,%s,n,z" % change_id


def format_commit_msg(pr, change_id=None):
    if GERRIT_TAG_REGEX.search(pr.body) == None:
        body = pr.body.strip() + "\n"
    else:
        body = pr.body.strip()
    return COMMIT_MSG_TEMPLATE.render(pr=pr, body=body, change_id=change_id)


# Assumes current directory and work tree
def get_last_change_id():
    header = str(sh.git('--no-pager', 'log', '-n', '1'))
    return list(CHANGE_ID_REGEX.finditer(header))[-1].group(1)


def do_review(pr):
    name = gerrit_name_for(pr.base.repo.name)
    ensure_repo(name)
    gh_name = pr.base.repo.name
    path = path_for_name(name)
    sh.cd(path)
    sh.git.reset('--hard')
    sh.git.checkout('master')
    if 'tmp' in sh.git.branch():
        sh.git.branch('-D', 'tmp')
    sh.git.checkout(pr.base.sha, '-b', 'tmp')
    logging.info('Attempting to download & apply patch on top of SHA %s' % pr.base.sha)
    sh.git.am(sh.curl(pr.patch_url))
    logging.info('Patch applied successfully')

    # Author of last patch is going to be the author of the commit on Gerrit. Hmpf
    author = sh.git('--no-pager', 'log', '--no-color', '-n', '1', '--format="%an <%ae>"')

    sh.git.checkout('master')

    branch_name = 'github/pr/%s' % pr.number

    is_new = True
    change_id = None

    if branch_name in sh.git.branch():
        is_new = False
        sh.git.checkout(branch_name)
        change_id = get_last_change_id()
        sh.git.checkout("master")
        sh.git.branch('-D', branch_name)
        logging.info('Patchset with Id %s already exists', change_id)
    else:
        is_new = True
        logging.info('Patchset not found, creating new')

    logging.info('Attempting to Squash Changes on top of %s in %s', pr.base.sha, branch_name)
    sh.git.checkout(pr.base.sha, '-b', branch_name)
    sh.git.merge('--squash', 'tmp')
    sh.git.commit('--author', author, '-m', format_commit_msg(pr, change_id=change_id))
    logging.info('Changes squashed successfully')
    if is_new:
        change_id = get_last_change_id()
        logging.info('New Change-Id is %s', change_id)
    logging.info('Attempting git review')
    sh.git.review('-t', branch_name)
    logging.info('git review successful')
    sh.git.checkout('master') # Set branch back to master when we're done
    if is_new:
        gh.repos(OWNER, gh_name).issues(pr.number).comments.post(body='Submitted to Gerrit: %s' % gerrit_url_for(change_id))
        logging.info('Left comment on Pull Request')

if __name__ == '__main__':
    name = sys.argv[1]
    pr_num = sys.argv[2]
    job_id = os.environ['JOB_ID']

    logging.basicConfig(format='%%(asctime)s %s PR#%s Job#%s %%(message)s' % (name, pr_num, job_id), filename=os.path.expanduser('~/logs/%s.process' % name), level=logging.INFO)
    try:
        do_review(get_pullreq(name, pr_num))
    except:
        gh.repos(OWNER, name).issues(pr_num).comments.post(body='Sorry, an error occured :( @yuvipanda will now be notified that job#%s did not end well' % job_id)
        logging.exception("Error!")
