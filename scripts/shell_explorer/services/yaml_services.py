import logging
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Optional, Union

import attr
import yaml

from scripts.shell_explorer.entities import Package, Repo, Shell2G, ShellL1
from scripts.shell_explorer.services import GhRepo

SHELL_TYPES = (Shell2G, ShellL1)
REPO_TYPES = (*SHELL_TYPES, Package)

if TYPE_CHECKING:
    T_SHELLS = Union[SHELL_TYPES]
    T_REPOS = Union[Shell2G, ShellL1, Package]


def yaml_str_to_repos_dict(yaml_str: str) -> dict[str, "T_REPOS"]:
    repos = yaml.load(yaml_str, Loader=yaml.Loader)
    return {repo.name: repo for repo in repos}


def repos_dict_to_yaml_str(repos_dict: dict[str, "T_REPOS"]) -> str:
    repos = sorted(repos_dict.values())
    return yaml.dump(repos, default_flow_style=False, sort_keys=False)


class RepoIsNotRecognized(Exception):
    def __init__(self, repo_name: str):
        self.repo_name = repo_name
        msg = f"Repository {repo_name} is not recognized as Shell2G, ShellL1 or Package"
        super().__init__(msg)


@attr.s(auto_attribs=True)
class SEWorkingRepo:
    SHELLS_FILE: ClassVar[str] = "shells.yaml"
    PACKAGES_FILE: ClassVar[str] = "packages.yaml"
    _se_repo: "GhRepo"
    working_branch: str

    def get_repos_container(self) -> "ReposContainer":
        return ReposContainer.from_yaml_strings(
            self._se_repo.get_file_data(self.SHELLS_FILE, self.working_branch),
            self._se_repo.get_file_data(self.PACKAGES_FILE, self.working_branch),
        )

    def _commit_file_if_changed(self, path: str, new_data: str):
        if self._se_repo.get_file_data(path, self.working_branch) != new_data:
            logging.info(f"Commit changes to {path}")
            message = f"ShellExplorer {path} {datetime.now()}"
            self._se_repo.update_file(path, message, new_data, self.working_branch)

    def commit_if_changed(self, repos_container: "ReposContainer"):
        for path, new_data in (
            (self.SHELLS_FILE, repos_container.shells_yaml_str),
            (self.PACKAGES_FILE, repos_container.packages_yaml_str),
        ):
            self._commit_file_if_changed(path, new_data)


@attr.s(auto_attribs=True)
class ReposContainer:
    _shells_dict: dict[str, "T_SHELLS"]
    _packages_dict: dict[str, "Package"]

    @classmethod
    def from_yaml_strings(
        cls, shells_yaml: str, packages_yaml: str
    ) -> "ReposContainer":
        return cls(
            yaml_str_to_repos_dict(shells_yaml),
            yaml_str_to_repos_dict(packages_yaml),
        )

    @property
    def shells_yaml_str(self) -> str:
        return repos_dict_to_yaml_str(self._shells_dict)

    @property
    def packages_yaml_str(self) -> str:
        return repos_dict_to_yaml_str(self._packages_dict)

    def get(
        self,
        repo_name: str,
    ) -> Optional["T_REPOS"]:
        return self._shells_dict.get(repo_name, self._packages_dict.get(repo_name))

    def add(self, repo: "Repo"):
        if isinstance(repo, SHELL_TYPES):
            self._shells_dict[repo.name] = repo
        elif isinstance(repo, Package):
            self._packages_dict[repo.name] = repo

    def create_repo_obj(self, gh_repo: "GhRepo") -> "T_REPOS":
        for r_type in REPO_TYPES:
            if r_type.is_type(gh_repo.name, gh_repo.ls("")):
                repo_obj = r_type(gh_repo.name, gh_repo.url)
                break
        else:
            raise RepoIsNotRecognized(gh_repo.name)

        self.add(repo_obj)
        return repo_obj

    def get_or_create_repo_obj(self, gh_repo: "GhRepo") -> "T_REPOS":
        if not (repo_obj := self.get(gh_repo.name)):
            repo_obj = self.create_repo_obj(gh_repo)
        return repo_obj

    def skip_repo(self, repo_obj: "Repo"):
        if isinstance(repo_obj, SHELL_TYPES):
            del self._shells_dict[repo_obj.name]
        else:
            del self._packages_dict[repo_obj.name]
