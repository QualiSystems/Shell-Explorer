from typing import TYPE_CHECKING, Iterable, Optional

import attr
from packaging.requirements import Requirement

from scripts.shell_explorer.entities import Shell2G
from scripts.shell_explorer.helpers import yaml_dump, yaml_load

if TYPE_CHECKING:
    from scripts.shell_explorer.services.yaml_services import T_SHELLS


@attr.s(auto_attribs=True, frozen=True, slots=True)
class PackageUsageContainer:
    _packages: dict[str, "PackageUsage"] = attr.ib(factory=dict)

    def get(self, package_name: str) -> Optional["PackageUsage"]:
        return self._packages.get(package_name)

    def get_or_create(self, package_name: str) -> "PackageUsage":
        if not (pu := self.get(package_name)):
            pu = PackageUsage(package_name)
            self._packages[package_name] = pu
        return pu

    def __iter__(self) -> Iterable["PackageUsage"]:
        return iter(self._packages.values())

    def to_yaml_str(self) -> str:
        return yaml_dump(self.to_yaml_dict())

    def to_yaml_dict(self) -> dict:
        return dict(map(PackageUsage.to_name_dict, sorted(self)))

    @classmethod
    def from_yaml_str(cls, yaml_str: str) -> "PackageUsageContainer":
        package_usage_dict = yaml_load(yaml_str)
        return cls(
            {
                name: PackageUsage.from_name_dict(name, specifiers)
                for name, specifiers in package_usage_dict.items()
            }
        )

    @classmethod
    def from_shell_repos(cls, shells: Iterable["T_SHELLS"]) -> "PackageUsageContainer":
        container = cls()
        for shell in filter(lambda s: isinstance(s, Shell2G), shells):
            for release in shell.releases:
                for dep in release.dependencies:
                    req = Requirement(dep)
                    package = container.get_or_create(req.name)
                    specifier = package.get_or_create(str(req.specifier) or "*")
                    pu_shell = specifier.get_or_create(shell.name)
                    pu_shell.add_tag(release.tag_name)
        return container


@attr.s(auto_attribs=True, frozen=True, slots=True)
class PackageUsage:
    name: str
    _specifiers: dict[str, "PackageSpecifier"] = attr.ib(cmp=False, factory=dict)

    def get(self, specifier: str) -> "PackageSpecifier":
        return self._specifiers.get(specifier)

    def get_or_create(self, specifier: str) -> "PackageSpecifier":
        if not (ps := self.get(specifier)):
            ps = PackageSpecifier(specifier)
            self._specifiers[specifier] = ps
        return ps

    def to_name_dict(self) -> tuple[str, dict]:
        return self.name, dict(map(PackageSpecifier.to_name_dict, sorted(self)))

    @classmethod
    def from_name_dict(cls, name, specifiers) -> "PackageUsage":
        return cls(
            name,
            {
                specifier: PackageSpecifier.from_name_dict(specifier, shells)
                for specifier, shells in specifiers.items()
            },
        )

    def __iter__(self) -> Iterable["PackageSpecifier"]:
        return iter(self._specifiers.values())


@attr.s(auto_attribs=True, frozen=True, slots=True)
class PackageSpecifier:
    specifier: str
    _shells: dict[str, "Shell"] = attr.ib(cmp=False, factory=dict)

    def get(self, shell_name: str) -> "Shell":
        return self._shells.get(shell_name)

    def get_or_create(self, shell_name: str) -> "Shell":
        if not (shell := self.get(shell_name)):
            shell = Shell(shell_name)
            self._shells[shell_name] = shell
        return shell

    def to_name_dict(self) -> tuple[str, dict]:
        return self.specifier, dict(map(Shell.to_name_list, sorted(self)))

    @classmethod
    def from_name_dict(cls, specifier: str, shells: dict) -> "PackageSpecifier":
        return cls(
            specifier,
            {
                shell_name: Shell.from_name_list(shell_name, tags)
                for shell_name, tags in shells.items()
            },
        )

    def __iter__(self) -> Iterable["Shell"]:
        return iter(self._shells.values())


@attr.s(auto_attribs=True, frozen=True, slots=True)
class Shell:
    name: str
    tags: set[str] = attr.ib(factory=set, cmp=False, converter=set)

    def add_tag(self, tag: str):
        self.tags.add(tag)

    def to_name_list(self) -> tuple[str, Iterable[str]]:
        return self.name, sorted(self.tags, reverse=True)

    @classmethod
    def from_name_list(cls, shell_name: str, tags: list["str"]) -> "Shell":
        return cls(shell_name, tags)
