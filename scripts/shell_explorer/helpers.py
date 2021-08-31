import enum
import re
from typing import Optional

from github.ContentFile import ContentFile
from packaging.specifiers import SpecifierSet


PYTHON_REQUIRES_PATTERN = re.compile(
    "python_requires\s*=\s*(\(?\s*['\"].+?['\"]\s*\)?)", re.DOTALL
)


class PyVersion(enum.Enum):
    PY2 = "PY2"
    PY3 = "PY3"
    PY2PY3 = "PY2PY3"


DEFAULT_PY_VERSION = PyVersion.PY2


def get_python_requires_str(setup_content: str) -> Optional[str]:
    try:
        output = PYTHON_REQUIRES_PATTERN.search(setup_content).group(1)
        python_requires = re.sub("[()\s'\"]", "", output)
    except AttributeError:
        python_requires = None
    return python_requires


def get_package_python_version(setup_content: str) -> PyVersion:
    python_requires = get_python_requires_str(setup_content)
    if not python_requires:
        return DEFAULT_PY_VERSION

    py2_set = {'2.7'}
    py3_set = {'3.7', '3.8', '3.9', '3.10'}
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
    return content.decoded_content.decode('utf-8')
