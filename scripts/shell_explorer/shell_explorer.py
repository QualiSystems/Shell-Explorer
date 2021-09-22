import json
import logging

from github import Github

from scripts.shell_explorer.pakcages_usage.entities import PackageUsageContainer
from scripts.shell_explorer.release_helpers import get_actual_releases
from scripts.shell_explorer.services import GhOrg
from scripts.shell_explorer.services.yaml_services import (
    RepoIsNotRecognized,
    ReposContainer,
    SEWorkingRepo,
)

EXPLORE_ORG = "QualiSystems"
WORKING_REPO = "Shell-Explorer"

logger = logging.getLogger(__name__)


class ShellExplorer:
    def __init__(
        self,
        gh_client: "Github",
        branch: str,
        new_releases: dict[str, list[int]],
        force_update: bool = False,
    ):
        self.branch = branch
        self.new_releases = new_releases
        self._gh_client = gh_client
        self._force_update = force_update

    @classmethod
    def from_cli(
        cls,
        auth_key: str,
        branch: str,
        new_releases_json: str,
        force_update: bool = False,
    ) -> "ShellExplorer":
        gh_client = Github(auth_key)
        return cls(
            gh_client,
            branch,
            json.loads(new_releases_json),
            force_update,
        )

    def _explore_releases(self, org: "GhOrg", repos_container: "ReposContainer"):
        for gh_repo in org.get_repos(self.new_releases):
            logger.info(f"Explore {gh_repo.name}")
            try:
                repo_obj = repos_container.get_or_create_repo_obj(gh_repo)
                if gh_releases := get_actual_releases(gh_repo.get_releases()):
                    if repo_obj.update_releases(gh_repo, gh_releases):
                        logger.debug(f"Added new releases {gh_repo}")
                else:
                    logger.debug(f"Skip repo {gh_repo.name} without releases")
                    repos_container.skip_repo(repo_obj)
            except RepoIsNotRecognized as e:
                logger.debug(str(e))

    def scan_and_commit(self):
        org = GhOrg.get_org(EXPLORE_ORG, self._gh_client)
        se_working_repo = SEWorkingRepo(org.get_repo(WORKING_REPO), self.branch)
        if self._force_update:
            repos_container = ReposContainer({}, {})
        else:
            repos_container = se_working_repo.get_repos_container()
        self._explore_releases(org, repos_container)
        se_working_repo.update_repo_files(repos_container)

        puc = PackageUsageContainer.from_shell_repos(repos_container.shells)
        se_working_repo.update_packages_usage(puc)
