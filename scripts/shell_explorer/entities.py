import functools
from functools import cached_property
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from github.GitRelease import GitRelease
    from packaging.version import Version


@functools.total_ordering
class Release(yaml.YAMLObject):
    yaml_tag = "!Release"

    def __init__(
        self,
        title,
        tag_name,
        published_at=None,
        release_url=None,
        python_version=None,
        dependencies=None,
    ):
        self.title = title
        self.tag_name = tag_name
        self.published_at = published_at
        self.release_url = release_url
        self.python_version = python_version
        self.dependencies = dependencies

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

    @cached_property
    def version(self) -> "Version":
        from scripts.shell_explorer.helpers import get_release_version

        return get_release_version(self)

    @classmethod
    def from_git_release(cls, git_release: "GitRelease") -> "Release":
        return cls(
            git_release.title,
            git_release.tag_name,
            git_release.published_at,
            git_release.html_url,
        )


@functools.total_ordering
class Repo(yaml.YAMLObject):
    yaml_tag = "!Repository"

    def __init__(self, name, url=None, releases=None):
        self.name = name
        self.url = url
        self.releases = releases or []

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


class Shell(Repo):
    yaml_tag = "!Shell"


class ShellL1(Repo):
    yaml_tag = "!Shell_L1"


class Shell1G(Repo):
    yaml_tag = "!Shell_1G"


class Shell2G(Repo):
    yaml_tag = "!Shell_2G"


class Package(Repo):
    yaml_tag = "!Package"
