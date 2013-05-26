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
OWNER = "wikimedia"
CHANGE_ID_REGEX = re.compile('Change-Id: (\w+)')
GERRIT_TEMPLATE = "ssh://suchabot@gerrit.wikimedia.org:29418/%s.git"
BOT_AUTHOR = "SuchABot <yuvipanda+suchabot@gmail.com>"
COMMIT_MSG_TEMPLATE = jinja2.Template("""{{pr.title}}

{{pr.body}}

GitHub: {{pr.html_url}}
{% if change_id %}Change-Id: {{change_id}} {% endif %}""")

with open(CONFIG_PATH) as f:
    config = yaml.load(f)
gh = github.GitHub(username=config['github']['username'], password=config['github']['password'])


def is_git_repo(path):
    return os.path.exists(path) and os.path.exists(os.path.join(path, '.git'))


def path_for_name(name):
    return os.path.join(WORKING_DIR, name.replace('/', '-'))


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
    return COMMIT_MSG_TEMPLATE.render(pr=pr, change_id=change_id)


# Assumes current directory and work tree
def get_last_change_id():
    header = str(sh.git('--no-pager', 'log', '-n', '1'))
    return list(CHANGE_ID_REGEX.finditer(header))[-1].group(1)


def do_review(pr):
    # FIXME: This breaks for any repo with a '-' in it's name itself
    # BLEH
    name = pr.base.repo.name.replace('-', '/')
    ensure_repo(name)
    gh_name = name.replace('/', '-')
    path = path_for_name(name)
    sh.cd(path)
    sh.git.reset('--hard')
    sh.git.checkout('master')
    if 'tmp' in sh.git.branch():
        sh.git.branch('-D', 'tmp')
    sh.git.checkout(pr.base.sha, '-b', 'tmp')
    logging.info('Attempting to download & apply patch on top of SHA1' % pr.base.sha)
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
    sh.git.review()
    logging.info('git review successful')
    sh.git.checkout('master') # Set branch back to master when we're done
    if is_new:
        gh.repos(OWNER, gh_name).issues(pr.number).comments.post(body='Submitted to Gerrit: %s' % gerrit_url_for(change_id))
        logging.info('Left comment on Pull Request')

if __name__ == '__main__':
    name = sys.argv[1]
    pr_num = sys.argv[2]
    job_id = os.environ['JOB_ID']

    logging.basicConfig(format='%%(asctime)s %s PR#%s Job#%s %%(message)s' % (name, pr_num, job_id), filename=os.path.expanduser('~/logs/%s.receive' % name), level=logging.INFO)
    do_review(get_pullreq(name, pr_num))
