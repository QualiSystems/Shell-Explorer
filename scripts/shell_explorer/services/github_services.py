from datetime import datetime
from typing import Iterable, Iterator, Optional, Union

import attr
from github import Github
from github.GithubException import GithubException
from github.GitRelease import GitRelease
from github.Organization import Organization
from github.Repository import Repository


class GhException(Exception):
    ...


@attr.s(auto_attribs=True, auto_exc=True)
class EmptyRepo(GhException):
    repo: "GhRepo"

    def __str__(self):
        return f"The repo {self.repo.name} is empty"


@attr.s(auto_attribs=True, auto_exc=True)
class NotFound(GhException):
    gh_repo: "GhRepo"
    path: str
    ref: str

    def __str__(self):
        return (
            f"File {self.path} not found in repository {self.gh_repo.name} "
            f"with ref {self.ref}"
        )


@attr.s(auto_attribs=True)
class GhOrg:
    _org: "Organization"

    def get_all_repos(self) -> Iterator["GhRepo"]:
        return map(GhRepo, self._org.get_repos())

    def get_repo(self, name: str) -> "GhRepo":
        return GhRepo(self._org.get_repo(name))

    def get_repos(self, repo_names: Optional[Iterable[str]]) -> Iterator["GhRepo"]:
        if repo_names:
            return map(self.get_repo, repo_names)
        else:
            return self.get_all_repos()

    @classmethod
    def get_org(cls, name: str, gh_client: "Github") -> "GhOrg":
        return cls(gh_client.get_organization(name))


@attr.s(auto_attribs=True)
class GhRepo:
    _git_repo: "Repository"

    def __attrs_post_init__(self):
        self.name: str = self._git_repo.name
        self.url: str = self._git_repo.html_url

    def get_file_data(self, path: str, ref: str) -> str:
        try:
            content = self._git_repo.get_contents(path, ref)
        except GithubException as e:
            if e.status == 404:
                raise NotFound(self, path, ref) from e
            else:
                raise
        else:
            return content.decoded_content.decode("utf-8")

    def ls(self, path: str) -> Iterable[str]:
        try:
            files = self._git_repo.get_contents(path)
        except GithubException as e:
            if "repository is empty" in str(e).lower():
                raise EmptyRepo(self) from e
            else:
                raise
        else:
            if not isinstance(files, list):
                files = [files]
            return (file.name for file in files)

    def get_releases(self, public: bool = True) -> Iterable["GhRelease"]:
        releases = self._git_repo.get_releases()
        if public:
            releases = filter(is_public_release, releases)
        return map(GhRelease, releases)

    def update_file(self, path: str, message: str, content: str, branch: str):
        c = self._git_repo.get_contents(path, branch)
        self._git_repo.update_file(path, message, content, c.sha, branch=branch)


def is_public_release(release: Union["GhRelease", "GitRelease"]) -> bool:
    return bool(release.published_at)


@attr.s(auto_attribs=True)
class GhRelease:
    _git_release: "GitRelease"

    def __attrs_post_init__(self):
        self.title: str = self._git_release.title
        self.tag_name: str = self._git_release.tag_name
        self.published_at: datetime = self._git_release.published_at
        self.url: str = self._git_release.html_url
