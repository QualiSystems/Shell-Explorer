from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Iterable, Union

from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from scripts.shell_explorer.entities import Release
    from scripts.shell_explorer.services import GhRelease

    T_RELEASE = Union[GhRelease, Release]

MAX_RELEASE_AGE_DAYS = 365


def get_release_version(release: "T_RELEASE") -> "Version":
    try:
        version = Version(release.tag_name)
    except InvalidVersion:
        version = Version("0")
    return version


def sort_releases_by_version(releases: Iterable["T_RELEASE"]) -> list["T_RELEASE"]:
    return sorted(releases, key=get_release_version, reverse=True)


def get_max_major_releases(releases: Iterable["T_RELEASE"]) -> list["T_RELEASE"]:
    versions: dict[int, "T_RELEASE"] = {}
    for release in releases:
        r_version = get_release_version(release)

        if not (max_major_release := versions.get(r_version.major)):
            versions[r_version.major] = release
        elif get_release_version(max_major_release) < r_version:
            versions[r_version.major] = release
    return sort_releases_by_version(versions.values())


def is_release_outdated(release: "T_RELEASE") -> bool:
    return datetime.now() - release.published_at > timedelta(days=MAX_RELEASE_AGE_DAYS)


def get_actual_releases(releases: Iterable["T_RELEASE"]) -> list["T_RELEASE"]:
    max_major_releases = get_max_major_releases(releases)
    for release in max_major_releases[1:].copy():
        if is_release_outdated(release):
            max_major_releases.remove(release)
    return max_major_releases


def is_releases_equal(
    releases: Iterable["Release"], gh_releases: Iterable["GhRelease"]
) -> bool:
    return {r.tag_name for r in releases} == {r.tag_name for r in gh_releases}
