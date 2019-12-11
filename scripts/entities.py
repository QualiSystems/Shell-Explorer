import datetime

import yaml


class Release(yaml.YAMLObject):
    yaml_tag = u"!Release"

    def __init__(self, title, tag_name, published_at=None, release_url=None, python_version=None):
        self.title = title
        self.tag_name = tag_name
        self.published_at = published_at
        self.release_url = release_url
        self.python_version = python_version

    def __hash__(self):
        return hash(self.title) ^ hash(self.tag_name)

    def __eq__(self, other):
        """
        :param Release other:
        """
        return self.title == other.title and self.tag_name == other.tag_name


class Repo(yaml.YAMLObject):
    yaml_tag = "!Repository"

    def __init__(self, name, url=None, releases=None):
        self.name = name
        self.url = url
        self.releases = releases or []

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        """
        :param Repo other:
        """
        return self.name == other.name


class Shell(Repo):
    yaml_tag = u"!Shell"

    # class TYPE:
    #     SHELL_L1 = "L1"
    #     SHELL_1G = "1G"
    #     SHELL_2G = "2G"
    #
    # shell_type = None

    # def __init__(self, name, url, releases=None):
    #     super().__init__(name, url, releases)
    #

    # def __hash__(self):
    #     return Repo.__hash__(self) | hash(self.shell_type)
    #
    # def __eq__(self, other):
    #     """
    #     :param Shell other:
    #     """
    #     return Repo.__eq__(self, other) and self.shell_type == other.shell_type


class ShellL1(Repo):
    yaml_tag = "!Shell_L1"
    # shell_type = Shell.TYPE.SHELL_L1

    # def __init__(self, name, url, releases=None):
    #     super().__init__(name, url, releases)
    #     self.shell_type = self.TYPE.SHELL_L1


class Shell1G(Repo):
    yaml_tag = "!Shell_1G"
    # shell_type = Shell.TYPE.SHELL_1G

    # def __init__(self, name, url, releases=None):
    #     super().__init__(name, url, releases)
    #     self.shell_type = self.TYPE.SHELL_1G


class Shell2G(Repo):
    yaml_tag = "!Shell_2G"
    # shell_type = Shell.TYPE.SHELL_2G

    # def __init__(self, name, url, releases=None):
    #     super().__init__(name, url, releases)
    #     self.shell_type = self.TYPE.SHELL_2G


class Package(Repo):
    yaml_tag = u"!Package"


if __name__ == '__main__':
    shell1 = Shell2G('Test Shell2', 'http://sfsdfsfsdf2')
    shell1.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell1.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))
    #
    shell2 = Shell2G('Test Shell1', 'http://sfsdfsfsdf1')
    shell2.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell2.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))

    shell3 = Shell1G('Test Shell2', 'http://sfsdfsfsdf2')
    shell3.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell3.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))

    shell4 = ShellL1('Test Shell4', 'http://sfsdfsfsdf2')
    shell4.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell4.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))

    shells = [shell1, shell2, shell3, shell4]
    shells = sorted(shells, key=lambda a: a.yaml_tag)

    dump = yaml.dump(shells, default_flow_style=False, sort_keys=False)

    print(dump)

    loaded = yaml.load(dump, Loader=yaml.Loader)
    print(loaded)
