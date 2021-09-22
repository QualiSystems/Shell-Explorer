import datetime

import yaml

from scripts.shell_explorer.entities import Release, Shell2G, ShellL1


def test_entities():
    shell1 = Shell2G("Test Shell2", "http://sfsdfsfsdf2")
    shell1.releases.append(
        Release(
            "Test Rel1", "1.2.3", datetime.datetime.now(), "http://fsafasf", 123, "PY2"
        )
    )
    shell1.releases.append(
        Release(
            "Test Rel2",
            "1.2.4",
            datetime.datetime.now(),
            "http://fsafasfff",
            124,
            "PY3",
        )
    )
    #
    shell2 = Shell2G("Test Shell1", "http://sfsdfsfsdf1")
    shell2.releases.append(
        Release(
            "Test Rel1", "1.2.3", datetime.datetime.now(), "http://fsafasf", 125, "PY2"
        )
    )
    shell2.releases.append(
        Release(
            "Test Rel2",
            "1.2.4",
            datetime.datetime.now(),
            "http://fsafasfff",
            126,
            "PY3",
        )
    )

    shell4 = ShellL1("Test Shell4", "http://sfsdfsfsdf2")
    shell4.releases.append(
        Release(
            "Test Rel1", "1.2.3", datetime.datetime.now(), "http://fsafasf", 127, "PY2"
        )
    )
    shell4.releases.append(
        Release(
            "Test Rel2",
            "1.2.4",
            datetime.datetime.now(),
            "http://fsafasfff",
            128,
            "PY3",
        )
    )

    shells = [shell1, shell2, shell4]
    shells = sorted(shells, key=lambda a: a.yaml_tag)

    dump = yaml.dump(shells, default_flow_style=False, sort_keys=False)
    loaded = yaml.load(dump, Loader=yaml.Loader)

    assert loaded == shells
