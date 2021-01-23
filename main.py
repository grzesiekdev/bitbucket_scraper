from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
import csv
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from os.path import basename
from email import encoders
from datetime import date
import config
import math


headers = {'Content-Type': 'application/json'}
auth = (config.request['user'], config.request['password'])
converter_email = config.converter_email['email']
sender = config.smtp['sender']
password = config.smtp['password']
receiver = config.smtp['receiver']
host = config.smtp['host']
port = config.smtp['port']
app_pass = config.smtp['app_pass']


class BranchRestriction(dict):
    """
    Get branch restrictions from specific branch
    """
    def __init__(self, kind, users, groups, pattern, restr_id):
        self.branch_restriction = {
                                'kind': kind,
                                'users': users,
                                'groups': groups,
                                'pattern': pattern,
                                'id': restr_id
                                }
        dict.__init__(self, branch_restriction={
                                'kind': kind,
                                'users': users,
                                'groups': groups,
                                'pattern': pattern,
                                'id': restr_id
                                })

    def __repr__(self):
        return str(self.branch_restriction)


class Branch(dict):
    """
    Get branches from specific repo
    """
    def __init__(self, name, branch_restriction):
        self.branch_name = name
        self.branch = {
                    'name': self.branch_name,
                    'branchRestrcitions': branch_restriction
                }
        dict.__init__(self, name=self.branch_name, branch_restriction=self.branch)

    def __repr__(self):
        return str(self.branch)


class Repo(dict):
    """
    Get repos from specific workspace
    """
    def __init__(self, name, branch):
        self.repo_name = name
        self.branch = {
                    'name': self.repo_name,
                    'branches': branch
                    }
        dict.__init__(self, name=self.repo_name, branch=self.branch)

    def __repr__(self):
        return str(self.branch)


class Workspace(dict):
    """
    Get workspaces, repos, branches, and restrictions and join them
    into single json format
    """
    def __init__(self, name, repos):
        self.workspace_name = name
        self.repo = {
            'workspace': self.workspace_name,
            'repos': repos
        }
        dict.__init__(self, name=self.workspace_name, repos=self.repo)

    def __repr__(self):
        return str(self.repo)


def get_workspace_repos(workspace):
    """
    Get all repos slugs from workspace
    """
    url = requests.get(f"https://bitbucket.org/api/2.0/repositories/{workspace}",
                       auth=auth,
                       headers=headers
                      )
    repos_pre = url.json()['values']
    repos = []
    for repo in repos_pre:
        repos.append(repo['slug'])
    return repos


def get_values(url):
    """
    Get values from passed endpoint
    """
    return url.json()['values']


def get_pages(url):
    """
    Get number of pages from passed endpoint
    """
    return url.json()['size'] // 10


def get_urls(pages, workspace, repository, branch):
    """
    Get endpoints for further calculations
    """
    urls = []
    if pages > 0:
        for page in range(1, pages+1):
            urls.append(f'https://bitbucket.org/api/2.0/repositories/'
                        f'{workspace}/{repository}/branch-restrictions/'
                        f'?page={page}&?pattern={branch}')
    else:
        urls.append(f'https://bitbucket.org/api/2.0/repositories/'
                    f'{workspace}/{repository}/branch-restrictions/'
                    f'?pattern={branch}')
    return urls


def get_users(value):
    """
    Get all users and groups from specific branch restriction
    """
    users = []
    groups = []
    if len(value['users']) > 0:
        for user in value['users']:
            if user in users:
                pass
            else:
                users.append(user['display_name'])
    if len(value['groups']) > 0:
        for group in value['groups']:
            if group['name'] in groups:
                pass
            else:
                groups.append(group['name'])
    return users, groups


def get_branch_restriction(workspace, repository, branch):
    """
    Get branch restrictions from passed branch
    """
    restrictions_endpoint = requests.get(f'https://bitbucket.org/api/2.0/'
                                         f'repositories/{workspace}/{repository}'
                                         f'/branch-restrictions/?pattern={branch}',
                                           auth=auth,
                                           headers=headers
                                        )
    values = get_values(restrictions_endpoint)
    pages = get_pages(restrictions_endpoint)
    urls = get_urls(pages, workspace, repository, branch)

    branch_restrictions = []
    for url in urls:
        new_url = requests.get(url,
                               auth=auth,
                               headers=headers
                               )

        values = new_url.json()['values']
        for value in values:
            users, groups = get_users(value)
            current = BranchRestriction(
                value['kind'],
                users,
                groups,
                value['pattern'],
                value['id']
            )
            branch_restrictions.append(current)
    return branch_restrictions


def get_repo_branches(workspace, repository):
    """
    Get all branches from passed repo
    """
    restrictions_endpoint = requests.get(f'https://bitbucket.org/api/2.0/'
                                         f'repositories/{workspace}/{repository}'
                                         '/branch-restrictions/',
                       auth=auth,
                       headers=headers
                    )
    print(restrictions_endpoint.text)
    values = get_values(restrictions_endpoint)
    pages = get_pages(restrictions_endpoint)
    urls = []
    patterns = []
    kinds = []
    branches = []
    if pages > 0:
        for page in range(1, pages+1):
            urls.append(f'https://bitbucket.org/api/2.0/repositories'
                        f'/{workspace}/{repository}/branch-restrictions/'
                        f'?page={page}')
    else:
        urls.append(f'https://bitbucket.org/api/2.0/repositories/'
                    f'{workspace}/{repository}/branch-restrictions/')
    for url in urls:
        new_url = requests.get(url,
                               auth=auth,
                               headers=headers
                               )
        values = new_url.json()['values']
        for value in values:
            pattern = value['pattern']
            if pattern in patterns:
                pass
            else:
                branch_restrictions = get_branch_restriction(
                                                            workspace,
                                                            repository,
                                                            pattern
                                                            )
                if value['kind'] not in kinds:
                    branches.append(Branch(
                        value['pattern'],
                        branch_restrictions)
                        )
                    kinds.append(value['kind'])
            patterns.append(pattern)
            kinds = []
    return branches


print('Preparing to connect with Bitbucket API')
WORKSPACE_ENDPOINT = 'https://bitbucket.org/api/2.0/user/permissions/workspaces/'
workspace_request = requests.get(
                        WORKSPACE_ENDPOINT,
                        auth=auth,
                        headers=headers
                    )
print('Connected. Scraping values from endpoints...')
workspaces_urls = math.ceil(workspace_request.json()['size'] / 50)
preformatted_urls = []
if workspaces_urls > 1:
    for i in range(1, workspaces_urls+1):
        preformatted_urls.append(WORKSPACE_ENDPOINT + f'?page={i}')
else:
    preformatted_urls.append(WORKSPACE_ENDPOINT)
output = []
workspaces_preformatted = []
for url in preformatted_urls:
    workspaces_preformatted.append(requests.get(
                            url,
                            auth=auth,
                            headers=headers
                        ).json()['values'])
workspaces = []
for workspace in workspaces_preformatted:
    for i in workspace:
        workspaces.append(i['workspace']["slug"])

for workspace in workspaces:
    repos = get_workspace_repos(workspace)
    repo_objs = []
    for repo in repos:
        branches = get_repo_branches(workspace, repo)
        repo_objs.append(Repo(repo, branches))
    workspace_obj = Workspace(workspace, repo_objs)
    output.append(workspace_obj)
print('Values scraped. Saving json into .csv')

with open('sth.json', 'w') as temp_file:
    temp_file.write(str(output))
CONVERTER_URL = 'https://json-csv.com/api/getcsv'
post_fields = {'email': converter_email, 'json': json.dumps(output)}
request = Request(CONVERTER_URL, urlencode(post_fields).encode())
csv_f = urlopen(request).read().decode()

with open('output.csv', 'w') as csv_file:
    csv_file.write(csv_f)

with open('output.csv', 'r') as readfile:
    reader = csv.reader(readfile)
    lines = []
    for row in reader:
        lines.append(row)
        if lines[0][0] == 'name':
            lines.remove(row)
with open('output.csv', 'w') as writeFile:
    writer = csv.writer(writeFile)
    for line in lines:
        # removing duplicated columns from output file
        for i in range(10):
            if i in [1, 2, 3, 4]:
                pass
    writer.writerows(lines)

print('Trying to send email with output.csv')

message = MIMEMultipart()
message['From'] = sender
message['To'] = receiver
message['Subject'] = f'Restrictions for {str(date.today())}'

message.attach(MIMEText('Output is in the attachment', 'plain'))
with open('output.csv', 'rb') as file:
    part = MIMEApplication(file.read(), Name=basename('output.csv'))
part['Content-Disposition'] = f'attachment; filename={basename("output.csv")}'
message.attach(part)

session = smtplib.SMTP(host, port)
session.starttls()
if host == 'smtp.gmail.com':
    session.login(sender, app_pass)
else:
    session.login(sender, password)
text = message.as_string()
session.sendmail(sender, receiver, text)
session.quit()
print('Mail Sent')
