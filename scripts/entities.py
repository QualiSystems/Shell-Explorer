import datetime

import yaml


class Release(yaml.YAMLObject):
    yaml_tag = u"!Release"

    def __init__(self, title, tag, published_at, release_url, python_version):
        self.title = title
        self.tag = tag
        self.published_at = published_at
        self.release_url = release_url
        self.python_version = python_version

    def __hash__(self):
        return hash(self.title) ^ hash(self.tag)

    def __eq__(self, other):
        """
        :param Release other:
        """
        return self.title == other.title and self.tag == other.tag


class Repo(yaml.YAMLObject):
    yaml_tag = "!Repository"

    def __init__(self, name, url, releases=None):
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
    yaml_tag = u'!Shell'

    class TYPE:
        SHELL_L1 = "L1"
        SHELL_1G = "1G"
        SHELL_2G = "2G"

    def __init__(self, name, url, shell_type, releases=None):
        self.shell_type = shell_type
        super().__init__(name, url, releases)


class Package(Repo):
    yaml_tag = u"!Package"


if __name__ == '__main__':
    shell1 = Shell('Test Shell2', Shell.TYPE.SHELL_2G, 'http://sfsdfsfsdf2')
    shell1.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell1.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))
    #
    shell2 = Shell('Test Shell1', Shell.TYPE.SHELL_1G, 'http://sfsdfsfsdf1')
    shell2.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell2.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))

    shell3 = Shell('Test Shell2', Shell.TYPE.SHELL_1G, 'http://sfsdfsfsdf2')
    shell3.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell3.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))

    shell4 = Shell('Test Shell4', Shell.TYPE.SHELL_2G, 'http://sfsdfsfsdf2')
    shell4.releases.append(Release('Test Rel1', '1.2.3', datetime.datetime.now(), 'http://fsafasf', 'PY2'))
    shell4.releases.append(Release('Test Rel2', '1.2.4', datetime.datetime.now(), 'http://fsafasfff', 'PY3'))

    shells = [shell1, shell2, shell3, shell4]
    shells = sorted(shells, key=lambda a: a.shell_type)

    dump = yaml.dump(shells, default_flow_style=False, sort_keys=False)

    print(dump)

    loaded = yaml.load(dump, Loader=yaml.Loader)
    print(loaded)
