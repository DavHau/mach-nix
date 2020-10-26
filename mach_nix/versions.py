import fnmatch
import sys
import traceback
from typing import Iterable, Tuple, List

from conda.common.compat import with_metaclass
from packaging.version import LegacyVersion
from conda.models.version import ver_eval, VersionOrder, SingleStrArgCachingType

from mach_nix.cache import cached
import packaging.version


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
    #return packaging.version.parse(ver_str)
    return Version(ver_str)


def ver_better_than_other(v: Version, o: Version) -> bool:
    return ver_eval(v, f">{o}")
    # instability = {v: 0, o: 0}
    # if v >= o:
    #     for ver in [v, o]:
    #         if ver.dev:
    #             instability[ver] += 2
    #         if ver.pre:
    #             instability[ver] += 1
    #     if instability[v] <= instability[o]:
    #         return True
    # return False


def ver_sort_key(ver: Version):
    """
    For sorting versions by preference in reversed order. (last elem == highest preference)
    """
    is_dev = 0
    is_rc = 0
    for component in ver.version:
        if len(component) > 1:
            for elem in component:
                if not isinstance(elem, str):
                    continue
                if 'dev' in elem.lower():
                    is_dev = 1
                    break
                if 'rc' in elem.lower():
                    is_rc = 1
                    break
    # if isinstance(ver, LegacyVersion):
    #     return 0, 0, 0, ver
    # is_dev = int(ver.is_devrelease)
    # is_pre = int(ver.is_prerelease)
    return not is_dev, not is_rc, ver


def best_version(versions: Iterable[Version]) -> Version:
    return sorted(versions)[-1]
    # best = None
    # for ver in versions:
    #     if best is None:
    #         best = ver
    #         continue
    #     if ver_better_than_other(ver, best):
    #         best = ver
    # return best


#@cached(keyfunc=lambda args: tuple(args[0]) + tuple(args[1]))
def filter_versions(
        versions: Iterable[Version],
        specs: Iterable[Tuple[str, str]]) -> List[Version]:
    """
    Reduces a given list of versions to contain only versions
    which are allowed according to the given specifiers
    """
    versions = list(versions)
    for op, ver in specs:
        if op == '==':
            if str(ver) == "*":
                return versions
            elif '*' in str(ver):
                op = '='
        ver = parse_ver(ver)
        versions = list(filter(lambda v: ver_eval(v, f"{op}{ver}"), versions))
        # if op == '==':
        #     versions_str = (str(ver) for ver in versions)
        #     versions_str_filtered = list(ver_str for ver_str in fnmatch.filter(versions_str, str(ver)))
        #     versions = [ver for ver in versions if str(ver) in versions_str_filtered]
        # elif op == '!=':
        #     versions_str = (str(ver) for ver in versions)
        #     bad_versions_str = set(fnmatch.filter(versions_str, str(ver)))
        #     versions = list(filter(lambda v: str(v) not in bad_versions_str, versions))
        # else:
        #     versions = list(filter(lambda v: eval(f'v {op} ver', dict(v=v, ver=ver)), versions))
    return list(versions)

