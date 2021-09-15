import json
import logging
import re
from copy import deepcopy
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

from github.GithubException import GithubException

from scripts.shell_explorer.entities import Package, Release, Repo, Shell2G, ShellL1
from scripts.shell_explorer.helpers import (
    DEFAULT_PY_VERSION,
    PyVersion,
    get_actual_releases,
    get_all_cloudshell_dependencies,
    get_package_python_version,
    get_packages_usage,
    get_str_from_git_content,
)
from scripts.shell_explorer.operations import RepoOperations, SerializationOperations

if TYPE_CHECKING:
    from github import Repository as GitRepository


class ShellExplorer:
    class CONFIG:
        EXPLORE_ORG = "Quali"
        WORKING_REPO = "Shell-Explorer"
        SHELLS_FILE = "shells.yaml"
        PACKAGES_FILE = "packages.yaml"
        PACKAGES_USAGE_FILE = "packages-usage.yaml"
        EXPLORE_RELEASES_DEPTH = 10
        MAX_RELEASE_AGE_DAYS = 365

    class CONST:
        SHELL_L1_FILES = {"main.py"}
        SHELL_1G_FILES = {"shell.yml", "deployment.xml"}
        SHELL_2G_FILES = {"shell-definition.yaml"}
        PACKAGE_FILES = {"setup.py"}
        NAME_PATTERN_L1 = re.compile(r"cloudshell-L1-.+", re.IGNORECASE)
        NAME_PATTERN_1G = re.compile(r".*shell.*", re.IGNORECASE)
        NAME_PATTERN_2G = re.compile(r".*2G.*", re.IGNORECASE)
        NAME_PATTERN_PACKAGE = re.compile(
            r"(cloudshell-.+|^shellfoundry$)", re.IGNORECASE
        )
        METADATA_FILE = "/src/drivermetadata.xml"
        SETUP_PY = "setup.py"
        PY_VER_PATTERN = re.compile(r"PythonVersion=(.+)\s")
        SHELL_2G_REQUIREMENTS = "src/requirements.txt"

    class VALUES:
        PYTHON_VERSION_2 = "PY2"
        PYTHON_VERSION_3 = "PY3"

    def __init__(self, auth_key, branch, new_releases):
        self.branch = branch
        self.new_releases: dict[str, list[int]] = json.loads(new_releases)
        self.repo_operations = RepoOperations(
            auth_key, self.CONFIG.EXPLORE_ORG, self.CONFIG.WORKING_REPO
        )
        self._repo_types = (
            (Package, self._is_it_a_package),
            (ShellL1, self.is_it_l1_shell),
            (Shell2G, self.is_it_2g_shell),
        )

    @property
    @lru_cache
    def _repo_shells(self):
        content = self.repo_operations.get_working_content(
            self.branch, self.CONFIG.SHELLS_FILE
        )
        return set(SerializationOperations.load_table(content))

    @property
    @lru_cache
    def _shells(self):
        return deepcopy(self._repo_shells)

    @property
    @lru_cache
    def _shells_dict(self):
        return {repo.name: repo for repo in self._shells}

    @property
    @lru_cache
    def _repo_packages(self):
        content = self.repo_operations.get_working_content(
            self.branch, self.CONFIG.PACKAGES_FILE
        )
        return set(SerializationOperations.load_table(content))

    @property
    @lru_cache
    def _packages(self):
        return deepcopy(self._repo_packages)

    @property
    @lru_cache
    def _packages_dict(self):
        return {repo.name: repo for repo in self._packages}

    def _match_by_content(self, content, file_list):
        if content.intersection(file_list) == file_list:
            return True

    def _match_by_name(self, pattern, name):
        return re.match(pattern, name)

    def _is_it_a_package(self, content, name):
        return self._match_by_name(
            self.CONST.NAME_PATTERN_PACKAGE, name
        ) and self._match_by_content(content, self.CONST.PACKAGE_FILES)

    def is_it_1g_shell(self, content, name):
        return self._match_by_name(
            self.CONST.NAME_PATTERN_1G, name
        ) or self._match_by_content(content, self.CONST.SHELL_1G_FILES)

    def is_it_2g_shell(self, content, name):
        return self._match_by_content(
            content, self.CONST.SHELL_2G_FILES
        ) or self._match_by_name(self.CONST.NAME_PATTERN_2G, name)

    def is_it_l1_shell(self, content, name):
        return self._match_by_name(
            self.CONST.NAME_PATTERN_L1, name
        ) and self._match_by_content(content, self.CONST.SHELL_L1_FILES)

    def _py3_ver_by_metadata(self, git_repo, release) -> bool:
        try:
            content = git_repo.get_contents(self.CONST.METADATA_FILE, release.tag_name)
            content = get_str_from_git_content(content)
            match = re.search(self.CONST.PY_VER_PATTERN, content)
        except Exception:
            result = False
        else:
            result = bool(match)
        return result

    def _get_shell_py_version(self, git_repo, release) -> "PyVersion":
        if self._py3_ver_by_metadata(git_repo, release):
            version = PyVersion.PY3
        else:
            version = PyVersion.PY2
        return version

    def _get_package_py_version(
        self, git_repo: "GitRepository", release: "Release"
    ) -> "PyVersion":
        try:
            content = git_repo.get_contents(self.CONST.SETUP_PY, release.tag_name)
            content = get_str_from_git_content(content)
            py_version = get_package_python_version(content)
        except Exception:
            msg = f"Could not get version for {git_repo.name} {release.tag_name}"
            logging.warning(msg, exc_info=True)
            py_version = DEFAULT_PY_VERSION
        return py_version

    def _get_py_version(
        self, git_repo: "GitRepository", repo_object: "Repo", release: "Release"
    ) -> str:
        if isinstance(repo_object, Package):
            py_version = self._get_package_py_version(git_repo, release)
        else:
            py_version = self._get_shell_py_version(git_repo, release)
        return py_version.value

    def _repo_releases(
        self, repo: "GitRepository", release_ids: Optional[list[str]]
    ) -> list["Release"]:
        if not release_ids:
            releases = [r for r in repo.get_releases() if r.published_at]
            releases = releases[: self.CONFIG.EXPLORE_RELEASES_DEPTH]
        else:
            releases = list(map(repo.get_release, release_ids))
        return get_actual_releases(map(Release.from_git_release, releases))

    def _extract_existing_repo(self, repo):
        return self._shells_dict.get(repo.name, self._packages_dict.get(repo.name))

    def _set_dependencies(self, release: "Release", git_repo: "GitRepository"):
        content = git_repo.get_contents(
            self.CONST.SHELL_2G_REQUIREMENTS, release.tag_name
        )
        content = get_str_from_git_content(content)
        release.dependencies = get_all_cloudshell_dependencies(
            content, release.python_version == "PY3"
        )

    def _create_repo_object(self, git_repo: "GitRepository") -> Optional["Repo"]:
        try:
            content = {c.name for c in git_repo.get_contents("")}
        except GithubException as e:
            if "repository is empty" not in str(e):
                raise
        else:
            for repo_class, check_func in self._repo_types:
                if check_func(content, git_repo.name):
                    repo_object = repo_class(git_repo.name, git_repo.html_url)
                    return repo_object

    def _explore_repo(
        self, git_repo: "GitRepository", release_ids: Optional[list[int]] = None
    ):
        logging.info(f"Explore {git_repo.name}")
        if repo_object := self._extract_existing_repo(
            git_repo
        ) or self._create_repo_object(git_repo):
            releases = self._repo_releases(git_repo, release_ids)
            if releases and releases != repo_object.releases:
                for r in releases:
                    r.python_version = self._get_py_version(git_repo, repo_object, r)
                repo_object.releases = releases

                if isinstance(repo_object, Package):
                    self._packages.add(repo_object)
                else:
                    self._shells.add(repo_object)
                logging.info(f"Added or updated {repo_object}")

    def _explore_releases(self):
        if not self.new_releases:
            for repo in self.repo_operations.get_org_repos():
                self._explore_repo(repo)
        else:
            for repo_name, release_ids in self.new_releases.items():
                repo = self.repo_operations.get_org_repo(repo_name)
                self._explore_repo(repo, release_ids)

    def scan_and_commit(self):
        self._explore_releases()
        self.repo_operations.commit_if_changed(
            SerializationOperations.dump_table(sorted(self._shells)),
            self.CONFIG.SHELLS_FILE,
            self.branch,
        )
        self.repo_operations.commit_if_changed(
            SerializationOperations.dump_table(sorted(self._packages)),
            self.CONFIG.PACKAGES_FILE,
            self.branch,
        )
        self.repo_operations.commit_if_changed(
            SerializationOperations.dump_table(get_packages_usage(self._shells)),
            self.CONFIG.PACKAGES_USAGE_FILE,
            self.branch,
        )
