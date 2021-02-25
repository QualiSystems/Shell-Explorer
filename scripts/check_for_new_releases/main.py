from collections import defaultdict
from datetime import datetime, timedelta
import sys

from github import Github, Repository, UnknownObjectException, Organization

REPO_NAME = "Shell-Explorer"
WORKFLOW_FILE_NAME = "check-for-new-releases.yml"
SHELL_EXPLORER_WORKFLOW_FILE_NAME = "shell-explorer.yml"


def get_time_of_last_run(repo: Repository) -> datetime:
    try:
        workflow = repo.get_workflow(WORKFLOW_FILE_NAME)
        last_run = next(iter(workflow.get_runs(branch='master')))
    except (UnknownObjectException, StopIteration):
        return datetime(2021, 1, 1)
    else:
        return last_run.created_at - timedelta(minutes=5)


def get_last_releases(org: Organization, check_from: datetime) -> dict[str, list[int]]:
    new_releases = defaultdict(list)
    for repo in org.get_repos():
        for release in repo.get_releases():
            if release.published_at and release.published_at >= check_from:
                new_releases[repo.name].append(repo.id)
            else:
                break
    return new_releases


def run_shell_explorer_workflow(repo: Repository, new_releases: dict[str, list[int]]):
    workflow = repo.get_workflow(SHELL_EXPLORER_WORKFLOW_FILE_NAME)
    workflow.create_dispatch("master", {"new_releases": new_releases})


def main(token: str):
    client = Github(token)
    org = client.get_organization("QualiSystems")
    repo = org.get_repo(REPO_NAME)
    check_from = get_time_of_last_run(repo)
    releases = get_last_releases(org, check_from)
    if releases:
        run_shell_explorer_workflow(repo, releases)


def run_from_cmd():
    token = sys.argv[1]
    main(token)


if __name__ == "__main__":
    run_from_cmd()
