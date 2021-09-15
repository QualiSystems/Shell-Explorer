import enum
import logging
import re
import sys
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Iterable, Optional

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version
from pip_download import PipDownloader

from scripts.shell_explorer.entities import Shell2G

if TYPE_CHECKING:
    from github.ContentFile import ContentFile

    from scripts.shell_explorer.entities import Release, Repo

PYTHON_REQUIRES_PATTERN = re.compile(
    r"python_requires\s*=\s*(\(?(\s*['\"].+?['\"]\s*)+\)?)", re.DOTALL
)


class PyVersion(enum.Enum):
    PY2 = "PY2"
    PY3 = "PY3"
    PY2PY3 = "PY2PY3"


DEFAULT_PY_VERSION = PyVersion.PY2
MAX_RELEASE_AGE_DAYS = 365


def set_logger():
    # remove default handlers
    logging.getLogger("root").handlers = []

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format=(
            "%(asctime)s [%(levelname)s]: %(name)s %(module)s"
            " - %(funcName)-20s %(message)s"
        ),
    )


def get_python_requires_str(setup_content: str) -> Optional[str]:
    try:
        output = PYTHON_REQUIRES_PATTERN.search(setup_content).group(1)
        python_requires = re.sub(r"[()\s'\"]", "", output)
    except AttributeError:
        python_requires = None
    return python_requires


def get_package_python_version(setup_content: str) -> PyVersion:
    python_requires = get_python_requires_str(setup_content)
    if not python_requires:
        return DEFAULT_PY_VERSION

    py2_set = {"2.7"}
    py3_set = {"3.7", "3.8", "3.9", "3.10"}
    specifier = SpecifierSet(python_requires)
    is_py2 = set(specifier.filter(py2_set))
    is_py3 = set(specifier.filter(py3_set))

    if is_py2 and is_py3:
        return PyVersion.PY2PY3
    elif is_py2:
        return PyVersion.PY2
    elif is_py3:
        return PyVersion.PY3
    else:
        return DEFAULT_PY_VERSION


def get_str_from_git_content(content: "ContentFile") -> str:
    return content.decoded_content.decode("utf-8")


def get_all_cloudshell_dependencies(requirements_text: str, is_py3: bool) -> list[str]:
    requirements = [req.strip() for req in requirements_text.splitlines()]
    py_version = "cp37" if is_py3 else "cp27"
    pip_downloader = PipDownloader([py_version], ["win"])
    all_requirements = pip_downloader.resolve_requirements_range(requirements)
    return [str(req) for req in all_requirements if req.name.startswith("cloudshell-")]


def get_packages_usage(shells: set["Repo"]) -> dict[str, dict[str, list[str]]]:
    """Returns a dict with packages and their version usage.

    Example, {
        'cloudshell-cli': {
            '<5,>=4.0': [
                'Juniper-JunOS-Firewall-Shell-2G',
                'Juniper-JunOS-Router-Shell-2G',
            ],
            '<3.4,>=3.3': ['FortiGate-FortiOS-Firewall-Shell-2G']
        }
    }
    """
    packages_usage = {}
    for shell in filter(lambda s: isinstance(s, Shell2G), shells):
        for release in shell.releases:
            for dep in getattr(release, "dependencies", []):
                req = Requirement(dep)
                specifier = str(req.specifier) or "*"
                package_specifiers = packages_usage.setdefault(req.name, {})
                package_specifiers.setdefault(specifier, []).append(shell.name)

    packages_usage = dict(sorted(packages_usage.items()))
    for package_name in packages_usage:
        packages_usage[package_name] = dict(
            sorted(packages_usage[package_name].items())
        )
    return packages_usage


def get_release_version(release: "Release") -> "Version":
    try:
        version = Version(release.tag_name)
    except InvalidVersion:
        version = Version("0")
    return version


def sort_releases_by_version(releases: Iterable["Release"]) -> list["Release"]:
    return sorted(releases, key=lambda r: r.version, reverse=True)


def get_max_major_releases(releases: Iterable["Release"]) -> list["Release"]:
    versions: dict[int, "Release"] = {}
    for release in releases:
        max_major_release = versions.get(release.version.major)
        if not max_major_release:
            versions[release.version.major] = release
        elif max_major_release.version < release.version:
            versions[release.version.major] = release
    return sort_releases_by_version(versions.values())


def is_release_outdated(release: "Release") -> bool:
    return datetime.now() - release.published_at > timedelta(days=MAX_RELEASE_AGE_DAYS)


def get_actual_releases(releases: Iterable["Release"]) -> list["Release"]:
    max_major_releases = get_max_major_releases(releases)
    for release in max_major_releases[1:].copy():
        if is_release_outdated(release):
            max_major_releases.remove(release)
    return max_major_releases
