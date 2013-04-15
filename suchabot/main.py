import os
import sys

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
BUG_TAGS = re.compile('Bug: (\w+)')
COMMIT_MSG_TEMPLATE = jinja2.Template("""{{pr.title}}

{{pr.body}}

Contains the following separate commits:

{{commit_summaries}}

GitHub: {{pr.html_url}}
{% for bug in bugs %}Bug: {{ bug }}
{% endfor %}
{% if change_id %}Change-Id: {{change_id}} {% endif %}""")

config = yaml.load(open(CONFIG_PATH))
gh = github.GitHub(username=config['github']['username'], password=config['github']['password'])

def is_git_repo(path):
    return os.path.exists(path) and os.path.exists(os.path.join(path, '.git'))

def path_for_name(name):
    return os.path.join(WORKING_DIR, name.replace('/', '-'))

def ensure_repo(name):
    if not os.path.exists(WORKING_DIR):
        sh.mkdir('-p', WORKING_DIR)
        log("Created working directory %s" % WORKING_DIR)
    fs_name = name.replace('/', '-')
    clone_folder = os.path.join(WORKING_DIR, fs_name)
    if is_git_repo(clone_folder):
        sh.cd(clone_folder)
        log("Repo found, updating...")
        sh.git.pull('origin', 'master')
        log("Updated!")
    else:
        log("Repo not found. Cloning...")
        sh.cd(WORKING_DIR)
        sh.git.clone(GERRIT_TEMPLATE % name, fs_name)
        log("Clone completed! Setting up git review...")
        sh.cd(fs_name)
        sh.git.remote('add', 'gerrit', GERRIT_TEMPLATE % name)
        sh.git.review('-s')
        log("git review setup!")

def get_pullreq(name, number):
    gh_name = name.replace('/', '-')
    pr = gh.repos(OWNER, gh_name).pulls(number).get()
    return pr

def gerrit_url_for(change_id):
    return "https://gerrit.wikimedia.org/r/#q,%s,n,z" % change_id

def format_commit_msg(pr, commit_summaries, change_id=None):
    bugs = []
    for bug_match in BUG_TAGS.finditer(commit_summaries):
        if bug_match.group(1) not in bugs:
            bugs.append(bug_match.group(1))
    commit_summaries = BUG_TAGS.replaceall(commit_summaries, "")
    return COMMIT_MSG_TEMPLATE.render(pr=pr, commit_summaries=commit_summaries, change_id=change_id, bugs=bugs)

# Assumes current directory and work tree
def get_last_change_id():
    header = str(sh.git('--no-pager', 'log', '-n', '1'))
    return list(CHANGE_ID_REGEX.finditer(header))[-1].group(1)

def log(s):
    print s

def do_review(name, pr):
    log("Syncing Repo %s for PR #%s" % (name, pr.number))
    gh_name = name.replace('/', '-')
    path = path_for_name(name)
    sh.cd(path)
    sh.git.reset('--hard')
    sh.git.checkout('master')
    if 'tmp' in sh.git.branch():
        sh.git.branch('-D', 'tmp')
    sh.git.checkout(pr.base.sha, '-b', 'tmp')
    log("Attempting to download patch")
    sh.git.am(sh.curl(pr.patch_url))
    log("Applied patch")

    commit_summaries = sh.git('--no-pager', 'log', '--no-color', 'master..tmp')
    # Author of last patch is going to be the author of the commit on Gerrit. Hmpf
    author = sh.git('--no-pager', 'log', '--no-color', '-n', '1', '--format="%an <%ae>"')

    sh.git.checkout('master')

    branch_name = 'github/pr/%s' % pr.number

    log("Topic Branch %s" % branch_name)

    if branch_name in sh.git.branch():
        log("Patchset already exists, based on %s" % pr.base.sha)
        sh.git.checkout(branch_name)
        change_id = get_last_change_id()
        sh.git.checkout("master")
        sh.git.branch('-D', branch_name)
        sh.git.checkout(pr.base.sha, '-b', branch_name)
        log("Patchset Change-Id: %s" % change_id)
        sh.git.reset('--hard', pr.base.sha)
        sh.git.merge('--squash', 'tmp')
        sh.git.commit('--author', author, '-m', format_commit_msg(pr, commit_summaries, change_id))
        log("Squashed commit successful. Attempting review")
        #gh.repos(OWNER, gh_name).issues(pr.number).comments.post(body='Updated in Gerrit: %s' % gerrit_url_for(change_id))
        sh.git.review()
        log("Review successful!")
    else:
        log("New patchset, based on %s" % pr.base.sha)
        sh.git.checkout(pr.base.sha, '-b', branch_name)
        sh.git.merge('--squash', 'tmp')
        sh.git.commit('--author', author, '-m', format_commit_msg(pr, commit_summaries))
        change_id = get_last_change_id()
        log("Patchset Change-Id: %s" % change_id)
        log("attempting review")
        sh.git.review() 
        log("Review successful!")
        gh.repos(OWNER, gh_name).issues(pr.number).comments.post(body='Submitted to Gerrit: %s' % gerrit_url_for(change_id))
        log("Left comment on Pull Request")

if __name__ == '__main__':
    name = sys.argv[1]
    pr_num = sys.argv[2]

    ensure_repo(name)
    do_review(name, get_pullreq(name, pr_num))
