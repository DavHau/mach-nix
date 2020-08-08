import fnmatch
import sys
import traceback
from typing import Iterable, Tuple, List

from packaging.version import Version, parse, LegacyVersion

from mach_nix.cache import cached


class PyVer(Version):
    def nix(self):
        res = 'python'
        res += str(self.release[0])
        if len(self.release) >= 2:
            res += str(self.release[1])
        return res

    def digits(self):
        return ''.join(filter(lambda c: c.isdigit(), str(self)))[:2]

    def python_version(self):
        return f"{self.release[0]}.{self.release[1]}"

    def python_full_version(self):
        try:
            return f"{self.release[0]}.{self.release[1]}.{self.release[2]}"
        except IndexError:
            traceback.print_exc()
            print("Error: please specify full python version including bugfix version (like 3.7.5)", file=sys.stderr)
            exit(1)


def ver_better_than_other(v: Version, o: Version) -> bool:
    # print(inspect.getfile(v.__class__))
    instability = {v: 0, o: 0}
    if v >= o:
        for ver in [v, o]:
            if ver.dev:
                instability[ver] += 2
            if ver.pre:
                instability[ver] += 1
        if instability[v] <= instability[o]:
            return True
    return False


def ver_lt_other(v: Version, o: Version) -> bool:
    return not (ver_better_than_other(v, o) or v == o)


def ver_sort_key(ver: Version):
    """
    For sorting versions by preference in reversed order. (last elem == highest preference)
    """
    if isinstance(ver, LegacyVersion):
        return 0, 0, 0, ver
    is_dev = int(ver.is_devrelease)
    is_pre = int(ver.is_prerelease)
    return 1, not is_dev, not is_pre, ver


def best_version(versions: Iterable[Version]) -> Version:
    best = None
    for ver in versions:
        if best is None:
            best = ver
            continue
        if ver_better_than_other(ver, best):
            best = ver
    return best


@cached(keyfunc=lambda args: tuple(args[0]) + tuple(args[1]))
def filter_versions(
        versions: Iterable[Version],
        specs: Iterable[Tuple[str, Version]]) -> List[Version]:
    """
    Reduces a given list of versions to contain only versions
    which are allowed according to the given specifiers
    """
    for op, ver in specs:
        ver = parse(ver)
        if op == '==':
            versions_str = (str(ver) for ver in versions)
            versions = (parse(ver) for ver in fnmatch.filter(versions_str, str(ver)))
        elif op == '!=':
            versions_str = (str(ver) for ver in versions)
            bad_versions_str = set(fnmatch.filter(versions_str, str(ver)))
            versions = list(filter(lambda v: str(v) not in bad_versions_str, versions))
        else:
            versions = list(filter(lambda v: eval(f'v {op} ver', dict(v=v, ver=ver)), versions))
    return list(versions)

