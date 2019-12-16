import os
import re
import sys
from collections import OrderedDict
from copy import deepcopy
from functools import lru_cache

from scripts.entities import Package, ShellL1, Shell2G, Shell1G, Release
from scripts.operations import RepoOperations, SerializationOperations
import logging

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s [%(levelname)s]: %(name)s %(module)s - %(funcName)-20s %(message)s")


class ShellExplorer(object):
    class CONFIG:
        EXPLORE_ORG = "Quali"
        WORKING_REPO = "Shell-Explorer"
        SHELLS_FILE = "shells.yaml"
        PACKAGES_FILE = "packages.yaml"
        EXPLORE_RELEASES_DEPTH = 5

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

    class VALUES:
        PYTHON_VERSION_2 = "PY2"
        PYTHON_VERSION_3 = "PY3"

    def __init__(self, auth_key, branch):
        self.branch = branch
        self.repo_operations = RepoOperations(auth_key, self.CONFIG.EXPLORE_ORG, self.CONFIG.WORKING_REPO)
        self._repo_type_dict = OrderedDict(
            [(Package, self._is_it_a_package),
             (ShellL1, self.is_it_l1_shell),
             (Shell2G, self.is_it_2g_shell),
             (Shell1G, self.is_it_1g_shell)])

    @property
    @lru_cache()
    def _repo_shells(self):
        return set(SerializationOperations.load_table(
            self.repo_operations.get_working_content(self.branch, self.CONFIG.SHELLS_FILE)))
        # with open("/tmp/shells_local.yaml", "r") as ff:
        #     return set(SerializationOperations.load_table(ff.read()))

    @property
    @lru_cache()
    def _shells(self):
        return deepcopy(self._repo_shells)

    @property
    @lru_cache()
    def _shells_dict(self):
        return {repo.name: repo for repo in self._shells}

    @property
    @lru_cache()
    def _repo_packages(self):
        return set(SerializationOperations.load_table(
            self.repo_operations.get_working_content(self.branch, self.CONFIG.PACKAGES_FILE)))
        # with open("/tmp/packages_local.yaml", "r") as ff:
        #     return set(SerializationOperations.load_table(ff.read()))

    @property
    @lru_cache()
    def _packages(self):
        return deepcopy(self._repo_packages)

    @property
    @lru_cache()
    def _packages_dict(self):
        return {repo.name: repo for repo in self._packages}

    def _match_by_content(self, content, file_list):
        if content.intersection(file_list) == file_list:
            return True

    def _match_by_name(self, pattern, name):
        return re.match(pattern, name)

    def _is_it_a_package(self, content, name):
        return self._match_by_name(self.CONST.NAME_PATTERN_PACKAGE,
                                   name) and self._match_by_content(content, self.CONST.PACKAGE_FILES)

    def is_it_1g_shell(self, content, name):
        return self._match_by_name(self.CONST.NAME_PATTERN_1G,
                                   name) or self._match_by_content(content, self.CONST.SHELL_1G_FILES)

    def is_it_2g_shell(self, content, name):
        return self._match_by_content(content, self.CONST.SHELL_2G_FILES) or self._match_by_name(
            self.CONST.NAME_PATTERN_2G, name)

    def is_it_l1_shell(self, content, name):
        return self._match_by_name(self.CONST.NAME_PATTERN_L1,
                                   name) and self._match_by_content(content, self.CONST.SHELL_L1_FILES)

    def _py_ver_by_rel_title(self, title):
        if self.VALUES.PYTHON_VERSION_3.lower() in title.lower():
            return self.VALUES.PYTHON_VERSION_3
        elif self.VALUES.PYTHON_VERSION_2.lower() in title.lower():
            return self.VALUES.PYTHON_VERSION_2

    def _py3_ver_by_metadata(self, git_repo, release):
        try:
            content = git_repo.get_contents(self.CONST.METADATA_FILE, release.tag_name)
        except Exception as e:
            content = None

        if content:
            match = re.search(self.CONST.PY_VER_PATTERN, content.decoded_content.decode("utf-8"))
            if match:
                return True

    def _py_version(self, git_repo, release):
        if self._py3_ver_by_metadata(git_repo, release):
            return self.VALUES.PYTHON_VERSION_3
        return self.VALUES.PYTHON_VERSION_2

    def _filter_releases_by_py_ver(self, git_repo, releases, existing_releases):
        """
        :param git_repo:
        :param list releases:
        :param list existing_releases:
        """
        version_dict = {}
        ex_rel_table = {r.match_str(): r for r in releases}
        for release in releases:
            if release not in existing_releases:
                release.python_version = self._py_version(git_repo, release)
            else:
                release = ex_rel_table.get(release.match_str())
            if release.python_version and release.python_version not in version_dict:
                version_dict[release.python_version] = release
        sorted_releases = sorted(version_dict.values(), reverse=True)
        logging.info("New releases: {}".format(sorted_releases))
        return sorted_releases

    def _repo_releases(self, repo):
        """
        :param github.Repository.Repository repo:
        :return:
        """
        releases = []
        for git_release in repo.get_releases():
            releases.append(self._create_release_object(git_release))
            if len(releases) >= self.CONFIG.EXPLORE_RELEASES_DEPTH:
                break
        return releases

    def _create_release_object(self, git_release):
        """
        :param github.GitRelease.GitRelease git_release:
        :return:
        """
        if git_release:
            return Release(git_release.title, git_release.tag_name, git_release.published_at, git_release.html_url)

    def _extract_existing_repo(self, repo):
        return self._shells_dict.get(repo.name, self._packages_dict.get(repo.name))

    def _explore_repo(self, repo):
        """
        :param github.Repository.Repository repo:
        :return:
        """
        logging.info("Explore {}".format(repo.name))
        repo_object = self._extract_existing_repo(repo)
        releases = self._repo_releases(repo)
        if not repo_object and releases:
            content = {c.name for c in repo.get_contents("")}
            repo_name = repo.name
            for repo_class, check_func in self._repo_type_dict.items():
                if check_func(content, repo_name):
                    logging.info("Adding {}".format(repo_name))
                    repo_object = repo_class(repo_name, repo.html_url)
                    break
        if not repo_object or not releases:
            return
        if releases[0] not in repo_object.releases:
            repo_object.releases = self._filter_releases_by_py_ver(repo, releases, repo_object.releases)
            if isinstance(repo_object, Package):
                self._packages.add(repo_object)
            else:
                self._shells.add(repo_object)

    def _explore_org(self):
        for repo in self.repo_operations.get_org_repos():
            self._explore_repo(repo)

    def scan_and_commit(self):
        self._explore_org()
        self.repo_operations.commit_if_changed(
            SerializationOperations.dump_table(sorted(list(self._shells))),
            self.CONFIG.SHELLS_FILE, self.branch)
        self.repo_operations.commit_if_changed(SerializationOperations.dump_table(sorted(list(self._packages))),
                                               self.CONFIG.PACKAGES_FILE, self.branch)


if __name__ == '__main__':
    # print(sys.argv)
    # username = sys.argv[1]
    # password = sys.argv[2]
    _auth_key = sys.argv[1]
    # _shells_file = sys.argv[2]
    # _organization = sys.argv[3]
    _branch = sys.argv[2]
    se = ShellExplorer(_auth_key, _branch)
    se.scan_and_commit()
