import re
import sys
from collections import OrderedDict
from copy import deepcopy
from difflib import Differ
from functools import lru_cache

import yaml
from github import Github

from scripts.entities import Repo, Package, ShellL1, Shell2G, Shell1G
from scripts.operations import RepoOperations, SerializationOperations


class ShellExplorer(object):
    class CONFIG:
        WORKING_ORG = "Quali"
        WORKING_REPO = "Shell-Explorer"
        SHELLS_FILE = "shells.yaml"
        PACKAGES_FILE = "packages.yaml"

    class CONST:
        SHELL_L1_FILES = {"main.py"}
        SHELL_1G_FILES = {"shell.yml", "deployment.xml"}
        SHELL_2G_FILES = {"shell-definition.yaml"}
        PACKAGE_FILES = {"setup.py"}
        NAME_PATTERN_L1 = re.compile(r"cloudshell-L1-.+", re.IGNORECASE)
        NAME_PATTERN_1G = re.compile(r".*shell.*", re.IGNORECASE)
        NAME_PATTERN_2G = re.compile(r".*2G.*", re.IGNORECASE)
        NAME_PATTERN_PACKAGE = re.compile(r"cloudshell-.+", re.IGNORECASE)
        METADATA_FILE = "/src/drivermetadata.xml"
        PY_VER_PATTERN = re.compile(r"PythonVersion=(.+)\s")

    class KEYS:
        SHELL_L1 = "SHELLS L1"
        SHELL_1G = "SHELLS 1G"
        SHELL_2G = "SHELLS 2G"
        PACKAGE = "PACKAGES"
        RELEASE_VERSION = "release_version"
        RELEASE_DATE = "release_date"
        REPO_URL = "url"
        PYTHON_VER = "python_version"

    class VALUES:
        PYTHON_VERSION_2 = "PY2"
        PYTHON_VERSION_3 = "PY3"

    TABLE_TEMPLATE = {KEYS.SHELL_L1: [], KEYS.SHELL_1G: [], KEYS.SHELL_2G: [], KEYS.PACKAGE: []}

    def __init__(self, auth_key, branch):
        self.branch = branch
        self.repo_operations = RepoOperations(auth_key, self.CONFIG.WORKING_ORG, self.CONFIG.WORKING_REPO)
        self._repo_type_dict = OrderedDict(
            [(Package, self._is_it_a_package),
             (ShellL1, self.is_it_L1_shell),
             (Shell2G, self.is_it_2G_shell),
             (Shell1G, self.is_it_1G_shell)])

    @property
    @lru_cache
    def _shells(self):
        return set(SerializationOperations.load_table(
            self.repo_operations.get_working_content(self.branch, self.CONFIG.SHELLS_FILE)))

    @property
    @lru_cache
    def _packages(self):
        return set(SerializationOperations.load_table(
            self.repo_operations.get_working_content(self.branch, self.CONFIG.PACKAGES_FILE)))

    def _match_by_content(self, content, file_list):
        if content.intersection(file_list) == file_list:
            return True

    def _match_by_name(self, pattern, name):
        return re.match(pattern, name)

    def _is_it_a_package(self, content, name):
        return self._match_by_name(self.CONST.NAME_PATTERN_PACKAGE, name) and self._match_by_content(content,
                                                                                                     self.CONST.PACKAGE_FILES)

    def is_it_1G_shell(self, content, name):
        return self._match_by_name(self.CONST.NAME_PATTERN_1G, name) or self._match_by_content(content,
                                                                                               self.CONST.SHELL_1G_FILES)

    def is_it_2G_shell(self, content, name):
        return self._match_by_content(content, self.CONST.SHELL_2G_FILES) or self._match_by_name(
            self.CONST.NAME_PATTERN_2G, name)

    def is_it_L1_shell(self, content, name):
        return self._match_by_name(self.CONST.NAME_PATTERN_L1, name) and self._match_by_content(content,
                                                                                                self.CONST.SHELL_L1_FILES)

    def _py_ver_by_rel_title(self, release):
        if self.VALUES.PYTHON_VERSION_3.lower() in release.title.lower():
            return self.VALUES.PYTHON_VERSION_3
        elif self.VALUES.PYTHON_VERSION_2.lower() in release.title.lower():
            return self.VALUES.PYTHON_VERSION_2

    def _py_ver_by_metadata(self, repo):
        try:
            content = repo.get_contents(self.CONST.METADATA_FILE)
        except Exception as e:
            content = None

        if content:
            match = re.search(self.CONST.PY_VER_PATTERN, content.decoded_content.decode("utf-8"))
            if match:
                return self.VALUES.PYTHON_VERSION_3
            else:
                return self.VALUES.PYTHON_VERSION_2
        else:
            return None

    def _collect_repo_data(self, repo, repo_from_file=None):
        """
        :param repo:
        :param scripts.entities.Repo repo_from_file:
        :return:
        """
        name = repo.name
        releases = list(repo.get_releases())
        if releases:
            latest_version = releases[0].tag_name
            url = repo.html_url
            py_ver = self._python_ver(repo)
            rel_date = releases[0].published_at
            repo_data = {
                name: {self.KEYS.RELEASE_VERSION: latest_version,
                       self.KEYS.RELEASE_DATE: rel_date,
                       self.KEYS.PYTHON_VER: py_ver,
                       self.KEYS.REPO_URL: url}}
            return repo_data

    def _extract_existing_repo(self, repo):
        repo = Repo(repo.name)
        shell = next(iter(self._shells.intersection({repo})), None)
        package = next(iter(self._packages.intersection({repo})), None)
        return shell if shell else package

    def _explore_repo(self, repo):
        repo_object = self._extract_existing_repo(repo)
        if not repo_object and next(iter(repo.releases), None):
            content = {c.name for c in repo.get_contents("")}
            repo_name = repo.name
            for repo_class, check_func in self._repo_type_dict.items():
                if check_func(content, repo_name):
                    repo_object = repo_class(repo_name, repo.html_url)
        else:
            return
        self._collect_repo_data(repo, repo_object)
        if repo_object.releases:
            if isinstance(repo_object, Package):
                self._packages.add(repo_object)
            else:
                self._shells.add(repo_object)


def _explore_org(self, branch):
    # table = deepcopy(self.TABLE_TEMPLATE)
    shells = set(self.repo_shells(branch))
    packages = set(self.repo_packages(branch))

    for repo in self.repo_operations.get_org_repos():

        result = self._explore_repo(repo, shells, packages)
        if not result:
            continue
        repo_type, data = result
        if repo_type and data:
            table[repo_type].append(data)
    return table


def scan_and_commit(self, path, branch):
    table = self._explore_org(self._org)
    data = yaml.dump(table, default_flow_style=False, allow_unicode=True, encoding=None)
    org = self._get_org(self._org)
    repo = org.get_repo()
    message = "Scanned Shells"
    ref = repo.get_branch(branch).commit.sha
    content = repo.get_contents(path, ref)
    repo_data = content.decoded_content.decode("utf-8")
    if not data == repo_data:
        result = repo.update_file(path, message, data, content.sha, branch=branch)
        print(result)


if __name__ == '__main__':
    # print(sys.argv)
    # username = sys.argv[1]
    # password = sys.argv[2]
    _auth_key = sys.argv[1]
    _shells_file = sys.argv[2]
    _organization = sys.argv[3]
    _branch = sys.argv[4]
    se = ShellExplorer(_auth_key, _organization)
    se.scan_and_commit(_shells_file, _branch)
