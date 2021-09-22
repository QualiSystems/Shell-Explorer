import enum
import re
from typing import Optional

import yaml
from packaging.specifiers import SpecifierSet
from pip_download import PipDownloader

PYTHON_REQUIRES_PATTERN = re.compile(
    r"python_requires\s*=\s*(\(?(\s*['\"].+?['\"]\s*)+\)?)", re.DOTALL
)
PY3_VERSION_PATTERN = re.compile(r"PythonVersion=(.+)\s")
MAX_RELEASE_AGE_DAYS = 365


class PyVersion(enum.Enum):
    PY2 = "PY2"
    PY3 = "PY3"
    PY2PY3 = "PY2PY3"


DEFAULT_PY_VERSION = PyVersion.PY2


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s]: %(name)s - "
            "%(funcName)-20s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "formatter": "default",
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "null_handler": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "scripts": {
            "level": "INFO",
            "handlers": ["console"],
        }
    },
    "root": {
        "level": "ERROR",
        "handlers": ["null_handler"],
    },
}


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


def get_py_version_from_shell_metadata(data: str) -> "PyVersion":
    try:
        v = PyVersion.PY3 if PY3_VERSION_PATTERN.search(data) else PyVersion.PY2
    except Exception:
        v = DEFAULT_PY_VERSION
    return v


class DependenciesInconsistent(Exception):
    ...


def get_all_cloudshell_dependencies(requirements_text: str, is_py3: bool) -> list[str]:
    requirements = [req.strip() for req in requirements_text.splitlines()]
    py_version = "cp37" if is_py3 else "cp27"
    pip_downloader = PipDownloader([py_version], ["win"])
    try:
        all_requirements = pip_downloader.resolve_requirements_range(requirements)
    except Exception as e:
        raise DependenciesInconsistent from e
    return [str(req) for req in all_requirements if req.name.startswith("cloudshell-")]


def yaml_load(yaml_str: str):
    return yaml.load(yaml_str, Loader=yaml.Loader)


def yaml_dump(data) -> str:
    return yaml.dump(data, default_flow_style=False, sort_keys=False)
