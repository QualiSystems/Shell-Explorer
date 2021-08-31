import functools

import yaml


@functools.total_ordering
class Release(yaml.YAMLObject):
    yaml_tag = u"!Release"

    def __init__(
        self, title, tag_name, published_at=None, release_url=None, python_version=None
    ):
        self.title = title
        self.tag_name = tag_name
        self.published_at = published_at
        self.release_url = release_url
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
        return "{yaml_tag}({title},{python_version})".format(
            yaml_tag=self.yaml_tag, **self.__dict__
        )

    def __repr__(self):
        return self.__str__()


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
        return "{yaml_tag}({name},{releases})".format(
            yaml_tag=self.yaml_tag, **self.__dict__
        )

    def __repr__(self):
        return self.__str__()


class Shell(Repo):
    yaml_tag = u"!Shell"


class ShellL1(Repo):
    yaml_tag = "!Shell_L1"


class Shell1G(Repo):
    yaml_tag = "!Shell_1G"


class Shell2G(Repo):
    yaml_tag = "!Shell_2G"


class Package(Repo):
    yaml_tag = u"!Package"
