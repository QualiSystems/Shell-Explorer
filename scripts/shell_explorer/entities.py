import functools
import logging
import re
from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Iterable, Optional

import yaml

from scripts.shell_explorer.helpers import (
    DEFAULT_PY_VERSION,
    PyVersion,
    get_all_cloudshell_dependencies,
    get_package_python_version,
    get_py_version_from_shell_metadata,
)
from scripts.shell_explorer.release_helpers import is_releases_equal

if TYPE_CHECKING:
    from scripts.shell_explorer.services import GhRelease, GhRepo


@functools.total_ordering
class Release(yaml.YAMLObject):
    yaml_tag = "!Release"

    def __init__(
        self,
        title: str,
        tag_name: str,
        published_at: datetime,
        release_url: str,
        release_id: int,
        python_version: str,
    ):
        self.title = title
        self.tag_name = tag_name
        self.published_at = published_at
        self.release_url = release_url
        self.release_id = release_id
        self.python_version = python_version

    def match_str(self):
        return self.title + self.tag_name

    def __hash__(self):
        return hash(self.match_str())

    def __eq__(self, other: "Release"):
        return self.title == other.title and self.tag_name == other.tag_name

    def __lt__(self, other: "Release"):
        return self.published_at < other.published_at

    def __str__(self):
        return f"{self.yaml_tag}({self.title},{self.python_version})"

    def __repr__(self):
        return self.__str__()


class Shell2GRelease(Release):
    yaml_tag = "!Shell2GRelease"

    def __init__(self, *args, dependencies: Optional[list[str]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependencies = dependencies or []


@functools.total_ordering
class Repo(yaml.YAMLObject):
    yaml_tag = "!Repository"

    def __init__(self, name: str, url: str, releases: Optional[list["Release"]] = None):
        self.name = name
        self.url = url
        self.releases: list["Release"] = releases or []

    def __hash__(self):
        return hash(self.yaml_tag) | hash(self.name)

    def __eq__(self, other: "Repo"):
        return self.yaml_tag == other.yaml_tag and self.name == other.name

    def __lt__(self, other: "Repo"):
        return (
            self.yaml_tag < other.yaml_tag
            or self.yaml_tag == other.yaml_tag
            and self.name < other.name
        )

    def __str__(self):
        return f"{self.yaml_tag}({self.name},{self.releases})"

    def __repr__(self):
        return self.__str__()

    @classmethod
    @abstractmethod
    def is_type(cls, repo_name: str, file_names: Iterable[str]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _create_new_releases(
        self, gh_repo: "GhRepo", gh_releases: Iterable["GhRelease"]
    ) -> list["Release"]:
        raise NotImplementedError

    def update_releases(
        self, gh_repo: "GhRepo", gh_releases: Iterable["GhRelease"]
    ) -> bool:
        if is_updated := not is_releases_equal(self.releases, gh_releases):
            self.releases = self._create_new_releases(gh_repo, gh_releases)
        return is_updated

    @abstractmethod
    def _get_py_version(self, gh_repo: "GhRepo", ref: str) -> "PyVersion":
        raise NotImplementedError


class Shell(Repo):
    yaml_tag = "!Shell"


class ShellL1(Shell):
    NAME_PATTERN = re.compile(r"cloudshell-l1-.+", re.I)
    yaml_tag = "!Shell_L1"

    @classmethod
    def is_type(cls, repo_name: str, file_names: Iterable[str]) -> bool:
        return cls.NAME_PATTERN.search(repo_name) and "main.py" in file_names

    def _get_py_version(self, gh_repo: "GhRepo", ref: str) -> "PyVersion":
        return PyVersion.PY2

    def _create_new_releases(
        self, gh_repo: "GhRepo", gh_releases: Iterable["GhRelease"]
    ) -> list["Release"]:
        return [
            Release(
                title=gh_r.title,
                tag_name=gh_r.tag_name,
                published_at=gh_r.published_at,
                release_url=gh_r.url,
                release_id=gh_r.id,
                python_version=self._get_py_version(gh_repo, gh_r.tag_name).value,
            )
            for gh_r in gh_releases
        ]


class Shell2G(Shell):
    METADATA_FILE = "/src/drivermetadata.xml"
    REQUIREMENTS_FILE = "src/requirements.txt"
    yaml_tag = "!Shell_2G"

    @classmethod
    def is_type(cls, repo_name: str, file_names: Iterable[str]) -> bool:
        return "shell-definition.yaml" in file_names

    def _get_py_version(self, gh_repo: "GhRepo", ref: str) -> "PyVersion":
        return get_py_version_from_shell_metadata(self._get_metadata(gh_repo, ref))

    def _get_metadata(self, gh_repo: "GhRepo", ref: str) -> str:
        return gh_repo.get_file_data(self.METADATA_FILE, ref)

    def _get_requirements(self, gh_repo: "GhRepo", ref: str) -> str:
        return gh_repo.get_file_data(self.REQUIREMENTS_FILE, ref)

    def _create_new_release(
        self, gh_repo: "GhRepo", gh_release: "GhRelease"
    ) -> "Shell2GRelease":
        py_v = self._get_py_version(gh_repo, gh_release.tag_name)
        dependencies = get_all_cloudshell_dependencies(
            self._get_requirements(gh_repo, gh_release.tag_name), py_v is py_v.PY3
        )
        return Shell2GRelease(
            title=gh_release.title,
            tag_name=gh_release.tag_name,
            published_at=gh_release.published_at,
            release_url=gh_release.url,
            release_id=gh_release.id,
            python_version=py_v.value,
            dependencies=dependencies,
        )

    def _create_new_releases(
        self, gh_repo: "GhRepo", gh_releases: Iterable["GhRelease"]
    ) -> list["Shell2GRelease"]:
        return [self._create_new_release(gh_repo, gh_r) for gh_r in gh_releases]


class Package(Repo):
    NAME_PATTERN = re.compile(r"(^cloudshell-.+|^shellfoundry$)", re.I)
    SETUP_FILE = "setup.py"
    yaml_tag = "!Package"
    releases: list["Release"]

    @classmethod
    def is_type(cls, repo_name: str, file_names: Iterable[str]) -> bool:
        return cls.NAME_PATTERN.search(repo_name) and "setup.py" in file_names

    def _get_py_version(self, gh_repo: "GhRepo", ref: str) -> "PyVersion":
        try:
            content = gh_repo.get_file_data(self.SETUP_FILE, ref)
            py_version = get_package_python_version(content)
        except Exception:
            msg = f"Could not get version for {gh_repo.name} {ref}"
            logging.warning(msg, exc_info=True)
            py_version = DEFAULT_PY_VERSION
        return py_version

    def _create_new_releases(
        self, gh_repo: "GhRepo", gh_releases: Iterable["GhRelease"]
    ) -> list["Release"]:
        return [
            Release(
                title=gh_r.title,
                tag_name=gh_r.tag_name,
                published_at=gh_r.published_at,
                release_url=gh_r.url,
                release_id=gh_r.id,
                python_version=self._get_py_version(gh_repo, gh_r.tag_name).value,
            )
            for gh_r in gh_releases
        ]
