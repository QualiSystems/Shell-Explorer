import logging
from datetime import datetime
from functools import cached_property, lru_cache

import yaml
from github import Github, Organization, Repository

from scripts.shell_explorer.helpers import get_str_from_git_content


class RepoOperations:
    def __init__(self, auth_key, org_name, working_repo):
        self._github = Github(auth_key)
        self._org_name = org_name
        self._working_repo = working_repo

    def _get_org(self, org_name):
        user = self._github.get_user()
        for org in user.get_orgs():
            if org.name == org_name:
                return org

    @cached_property
    def org(self) -> Organization:
        return self._get_org(self._org_name)

    @property
    @lru_cache
    def working_repo(self):
        return self.org.get_repo(self._working_repo)

    def get_org_repos(self):
        return self.org.get_repos()

    def get_org_repo(self, name: str) -> Repository:
        return self.org.get_repo(name)

    def get_working_content(self, branch, path) -> str:
        ref = self.working_repo.get_branch(branch).commit.sha
        content = self.working_repo.get_contents(path, ref)
        return get_str_from_git_content(content)

    def commit_if_changed(self, data, path, branch):
        ref = self.working_repo.get_branch(branch).commit.sha
        content = self.working_repo.get_contents(path, ref)
        repo_data = get_str_from_git_content(content)
        if data != repo_data:
            logging.info(f"Commit changes to {path}")
            message = f"ShellExplorer {path} {datetime.now()}"
            return self.working_repo.update_file(
                path, message, data, content.sha, branch=branch
            )


class SerializationOperations:
    @staticmethod
    def load_table(data):
        return yaml.load(data, Loader=yaml.Loader)

    @staticmethod
    def dump_table(table):
        return yaml.dump(table, default_flow_style=False, sort_keys=False)
