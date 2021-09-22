import logging.config

import click

from scripts.check_for_new_releases.main import main as check_for_new_releases
from scripts.shell_explorer.helpers import LOGGING_CONFIG
from scripts.shell_explorer.shell_explorer import ShellExplorer

logging.config.dictConfig(LOGGING_CONFIG)


@click.group()
def cli():
    pass


@cli.command("explore")
@click.option("--auth-key", required=True)
@click.option("--branch", required=True, default="dev")
@click.option(
    "--new-releases",
    required=False,
    default="{}",
    help="Json dict of repositories and release ids. {<repo_name>: [<release_id1>]}",
)
@click.option("--force-update", is_flag=True, default=False)
def shell_explorer(auth_key: str, branch: str, new_releases: str, force_update: bool):
    se = ShellExplorer.from_cli(auth_key, branch, new_releases, force_update)
    se.scan_and_commit()


@cli.command(
    "check-new-releases",
    help="Looks for new releases and triggers GA for ShellExplorer",
)
@click.option("--auth-key", required=True)
def check_new_releases(auth_key: str):
    check_for_new_releases(auth_key)


if __name__ == "__main__":
    cli()
