import datetime

import yaml

from scripts.shell_explorer.entities import Shell2G, Release, Shell1G, ShellL1


def test_entities():
    shell1 = Shell2G("Test Shell2", "http://sfsdfsfsdf2")
    shell1.releases.append(
        Release("Test Rel1", "1.2.3", datetime.datetime.now(), "http://fsafasf", "PY2")
    )
    shell1.releases.append(
        Release(
            "Test Rel2", "1.2.4", datetime.datetime.now(), "http://fsafasfff", "PY3"
        )
    )
    #
    shell2 = Shell2G("Test Shell1", "http://sfsdfsfsdf1")
    shell2.releases.append(
        Release("Test Rel1", "1.2.3", datetime.datetime.now(), "http://fsafasf", "PY2")
    )
    shell2.releases.append(
        Release(
            "Test Rel2", "1.2.4", datetime.datetime.now(), "http://fsafasfff", "PY3"
        )
    )

    shell3 = Shell1G("Test Shell2", "http://sfsdfsfsdf2")
    shell3.releases.append(
        Release("Test Rel1", "1.2.3", datetime.datetime.now(), "http://fsafasf", "PY2")
    )
    shell3.releases.append(
        Release(
            "Test Rel2", "1.2.4", datetime.datetime.now(), "http://fsafasfff", "PY3"
        )
    )

    shell4 = ShellL1("Test Shell4", "http://sfsdfsfsdf2")
    shell4.releases.append(
        Release("Test Rel1", "1.2.3", datetime.datetime.now(), "http://fsafasf", "PY2")
    )
    shell4.releases.append(
        Release(
            "Test Rel2", "1.2.4", datetime.datetime.now(), "http://fsafasfff", "PY3"
        )
    )

    shells = [shell1, shell2, shell3, shell4]
    shells = sorted(shells, key=lambda a: a.yaml_tag)

    dump = yaml.dump(shells, default_flow_style=False, sort_keys=False)
    loaded = yaml.load(dump, Loader=yaml.Loader)

    assert loaded == shells
