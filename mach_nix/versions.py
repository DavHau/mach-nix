import sys
import traceback
from typing import Iterable, Tuple, List

import packaging.version
from conda.common.compat import with_metaclass
from conda.models.version import ver_eval, VersionOrder, SingleStrArgCachingType
from packaging.version import LegacyVersion

from mach_nix.cache import cached


@with_metaclass(SingleStrArgCachingType)
class Version(VersionOrder):
    pass


class PyVer(Version):
    def __init__(self, vstr):
        self.pypa_ver = packaging.version.Version(vstr)
        super(PyVer, self).__init__(vstr)
    def nix(self):
        res = 'python'
        res += str(self.pypa_ver.release[0])
        if len(self.pypa_ver.release) >= 2:
            res += str(self.pypa_ver.release[1])
        return res

    def digits(self):
        return ''.join(filter(lambda c: c.isdigit(), str(self.pypa_ver)))[:2]

    def python_version(self):
        return f"{self.pypa_ver.release[0]}.{self.pypa_ver.release[1]}"

    def python_full_version(self):
        try:
            return f"{self.pypa_ver.release[0]}.{self.pypa_ver.release[1]}.{self.pypa_ver.release[2]}"
        except IndexError:
            traceback.print_exc()
            print("Error: please specify full python version including bugfix version (like 3.7.5)", file=sys.stderr)
            exit(1)


def parse_ver(ver_str) -> Version:
    return Version(ver_str)


def ver_better_than_other(v: Version, o: Version) -> bool:
    return ver_eval(v, f">{o}")


def ver_sort_key(ver: Version):
    """
    For sorting versions by preference in reversed order. (last elem == highest preference)
    """
    is_dev = 0
    is_pre = 0
    for component in ver.version:
        if len(component) > 1:
            for elem in component:
                if not isinstance(elem, str):
                    continue
                if 'dev' in elem.lower():
                    is_dev = 1
                    break
                # contains letters == pre-release
                if elem.lower().islower():
                    is_pre = 1
                    break
    return not is_dev, not is_pre, ver


def best_version(versions: Iterable[Version]) -> Version:
    return sorted(versions)[-1]


@cached(keyfunc=lambda args: hash(tuple(args[0]) + tuple(args[1])))
def filter_versions(
        versions: List[Version],
        specs: List[Tuple[str, str]]) -> List[Version]:
    """
    Reduces a given list of versions to contain only versions
    which are allowed according to the given specifiers
    """
    versions = list(versions)
    assert len(versions) > 0
    for op, ver in specs:
        if op == '==':
            if str(ver) == "*":
                return versions
            elif '*' in str(ver):
                op = '='
        ver = parse_ver(ver)
        versions = list(filter(lambda v: ver_eval(v, f"{op}{ver}"), versions))
    return list(versions)

