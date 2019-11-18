import re
import sys
from collections import OrderedDict
from copy import deepcopy

import yaml
from github import Github


class ShellExplorer(object):
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
        LATEST_VERSION = "version"
        REPO_URL = "url"
        PYTHON_VER = "python_version"

    class VALUES:
        PYTHON_VERSION_2 = "PY2"
        PYTHON_VERSION_3 = "PY3"

    TABLE_TEMPLATE = {KEYS.SHELL_L1: [], KEYS.SHELL_1G: [], KEYS.SHELL_2G: [], KEYS.PACKAGE: []}

    def __init__(self, auth_key, org=None):
        self.github = Github(auth_key)
        self._org = org
        # self.shells_table = {self.KEYS.SHELL_L1: [], self.KEYS.SHELL_1G: [], self.KEYS.SHELL_2G: [],
        #                      self.KEYS.PACKAGE: []}
        self._repo_type_dict = OrderedDict(
            [(self.KEYS.PACKAGE, self._is_it_a_package),
             (self.KEYS.SHELL_L1, self.is_it_L1_shell),
             (self.KEYS.SHELL_2G, self.is_it_2G_shell),
             (self.KEYS.SHELL_1G, self.is_it_1G_shell)])

    def _get_org(self, org_name):
        user = self.github.get_user()
        for org in user.get_orgs():
            if org.name == org_name:
                return org

    def _get_org_repos(self, org):
        org = self._get_org(org)
        if org:
            return org.get_repos()
        else:
            return []

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

    def _python_ver(self, repo):
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

    def _collect_repo_data(self, repo):
        name = repo.name
        releases = list(repo.get_releases())
        if releases:
            latest_version = releases[0].tag_name
            url = repo.html_url
            py_ver = self._python_ver(repo)
            repo_data = {
                name: {self.KEYS.LATEST_VERSION: latest_version,
                       self.KEYS.PYTHON_VER: py_ver,
                       self.KEYS.REPO_URL: url}}
            return repo_data

    def _explore_repo(self, repo):
        try:
            content = set([c.name for c in repo.get_contents("")])
            repo_name = repo.name
        except Exception as e:
            return
        for repo_type, check_func in self._repo_type_dict.items():
            if check_func(content, repo_name):
                data = self._collect_repo_data(repo)
                return repo_type, data

    def _explore_org(self, org):
        table = deepcopy(self.TABLE_TEMPLATE)
        for repo in self._get_org_repos(org):
            result = self._explore_repo(repo)
            if not result:
                continue
            repo_type, data = result
            if repo_type and data:
                table[repo_type].append(data)
        return table

    @staticmethod
    def _save(path, table):
        with open(path, "w") as file_descr:
            data = yaml.dump(table, default_flow_style=False, allow_unicode=True, encoding=None)
            file_descr.write(data)

    def scan_to_file(self, path):
        table = self._explore_org(self._org)
        self._save(path, table)

    def update_repo(self, repo_name, path):
        pass


if __name__ == '__main__':
    # print(sys.argv)
    # username = sys.argv[1]
    # password = sys.argv[2]
    organization = "Quali"
    shells_file = sys.argv[2]
    se = ShellExplorer(sys.argv[1], organization)
    se.scan_to_file(shells_file)
