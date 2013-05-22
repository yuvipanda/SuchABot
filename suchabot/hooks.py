import argparse
import getpass
import sys

import github

gh = None

def login(username, password):
    global gh
    gh = github.GitHub(username=username, password=password)

def add_hook(owner, repo, hook, url):
    try:
        gh.repos(owner, repo).hooks().post(name='web', 
                active=True,
                events=[hook],
                config={
                    'url': url
                    }
                )
    except github.ApiError as e:
        print "Error in adding hook. Server responded with " +  e.response.json


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add arbitrary hooks to a repostiory')
    parser.add_argument('-u', '--username', help='Your GitHub Username')
    parser.add_argument('-R', '--repo', help='Full repository name to target (in form owner/repo)')
    parser.add_argument('-H', '--hook', help='Name of hook to add')
    parser.add_argument('-U', '--url', help='Url the hook should post to')
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    password = getpass.getpass("Enter your GitHub Password: ")

    login(args.username, password)
    owner, repo = args.repo.split('/')
    add_hook(owner, repo, args.hook, args.url)
