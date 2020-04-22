import json
import sys
from collections import UserDict
from dataclasses import dataclass
from typing import List, Tuple

import distlib.markers
from packaging.version import Version, parse

from mach_nix.requirements import strip_reqs_by_marker, Requirement, parse_reqs, context
from mach_nix.versions import PyVer
from .bucket_dict import LazyBucketDict


class DependencyDB(UserDict):
    def __init__(self, py_ver: PyVer, data_dir, *args, **kwargs):
        super(DependencyDB, self).__init__(*args, **kwargs)
        self.data = LazyBucketDict(data_dir)
        self.context = context(py_ver)
        self.py_ver_digits = py_ver.digits()
        for name, releases in self.data.items():
            key = self._unify_key(name)
            if key != name:
                self.data[key] = self.data[name]
                del self.data[name]

    def __getitem__(self, item) -> dict:
        result = {}
        for ver, pyvers in self.data[self._unify_key(item)].items():
            if self.py_ver_digits in pyvers:
                if isinstance(pyvers[self.py_ver_digits], str):
                    result[ver] = pyvers[pyvers[self.py_ver_digits]]
                else:
                    result[ver] = pyvers[self.py_ver_digits]
        return result

    def exists(self, name, ver=None):
        try:
            key = self._unify_key(name)
            pkg = self[key]
        except KeyError:
            return False
        if ver:
            return pkg['ver'] == ver
        return True

    def _unify_key(self, key: str) -> str:
        return key.replace('_', '-').lower()

    def get_pkg_reqs(self, pkg_name, pkg_version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get requirements for package
        """
        ver_str = str(pkg_version)
        if not self.exists(pkg_name) or ver_str not in self[pkg_name]:
            raise Exception(f'Cannot find {pkg_name}:{pkg_version} in db')
        pkg = self[pkg_name][ver_str]
        requirements = dict(
            setup_requires=[],
            install_requires=[]
        )
        for t in ("setup_requires", "install_requires"):
            if t not in pkg:
                requirements[t] = []
            else:
                reqs_raw = pkg[t]
                reqs = list(parse_reqs(reqs_raw))
                requirements[t] = list(strip_reqs_by_marker(reqs, self.context))
        extras = set(extras) if extras else []
        if 'extras_require' in pkg:
            for name, reqs_str in pkg['extras_require'].items():
                # handle extras with marker in key
                if ':' in name:
                    name, marker = name.split(':')
                    if not distlib.markers.interpret(marker, self.context):
                        continue
                # handle if extra's key only contains marker. like ':python_version < "3.7"'
                if name == '' or name in extras:
                    requirements['install_requires'] += list(strip_reqs_by_marker(list(parse_reqs(reqs_str)), self.context))

        return requirements['install_requires'], requirements['setup_requires']

    def available_versions(self, pkg_name: str) -> List[Version]:
        name = pkg_name.replace("_", "-").lower()
        if self.exists(name):
            return [parse(ver) for ver in self[name].keys()]
        error_text = \
            f"\nThe Package '{pkg_name}' cannot be found in the dependency DB used by mach-nix. \n" \
            f"Please check the following:\n" \
            f"  1. Does the package actually exist on pypi? Please check https://pypi.org/project/{pkg_name}/\n" \
            f"  2. Does the package's initial release date predate the mach-nix release date? \n" \
            f"     If so, either upgrade mach-nix itself or manually specify 'pypi_deps_db_commit' and\n" \
            f"     'pypi_deps_db_sha256 for a newer commit of https://github.com/DavHau/pypi-deps-db/commits/master\n" \
            f"If none of that works, there was probably a problem while extracting dependency information by the crawler " \
            f"maintaining the database.\n" \
            f"Please open an issue here: https://github.com/DavHau/pypi-crawlers/issues/new\n"
        print(error_text, file=sys.stderr)
        exit(1)


@dataclass
class NixpkgsPyPkg:
    nix_key: str
    ver: Version


class NixpkgsDirectory(UserDict):
    def __init__(self, nixpkgs_json_file, **kwargs):
        with open(nixpkgs_json_file) as f:
            data = json.load(f)
        self.by_nix_key = {}
        for nix_key, version in data.items():
            if not version:
                continue
            self.by_nix_key[nix_key] = NixpkgsPyPkg(
                nix_key=nix_key,
                ver=parse(version)
            )
        self.data = {}
        for nix_key, pkg in self.by_nix_key.items():
            key = self._unify_key(nix_key)
            if key not in self.data:
                self.data[key] = []
            # Skip if version already exists. Prevents infinite recursions in nix (see 'pytest' + 'pytest_5')
            elif any(existing_pkg.ver == pkg.ver for existing_pkg in self.data[key]):
                continue
            self.data[key].append(pkg)
        super(NixpkgsDirectory, self).__init__(self.data, **kwargs)

    def __getitem__(self, item) -> NixpkgsPyPkg:
        return self.data[self._unify_key(item)][-1]

    def has_multiple_candidates(self, name):
        return len(self.data[self._unify_key(name)]) > 1

    def get_all_candidates(self, name) -> List[NixpkgsPyPkg]:
        return self.data[self._unify_key(name)]

    def get_highest_ver(self, pkgs: List[NixpkgsPyPkg]):
        return max(pkgs, key=lambda p: p.ver)

    @staticmethod
    def is_same_ver(ver1, ver2, ver_idx):
        if any(not ver.release or len(ver.release) <= ver_idx for ver in (ver1, ver2)):
            return False
        return ver1.release[ver_idx] == ver2.release[ver_idx]

    def find_best_nixpkgs_candidate(self, name, ver):
        """
        In case a python package has more than one candidate in nixpkgs
        like `django` and `django_2_2`, this algo will select the right one.
        """
        pkgs: List[NixpkgsPyPkg] = sorted(self.get_all_candidates(name), key=lambda pkg: pkg.ver)
        if len(pkgs) == 1:
            return self[name].nix_key
        # try to find nixpkgs candidate with closest version
        remaining_pkgs = pkgs
        for i in range(7):  # usually there are not more than 4 parts in a version
            same_ver = list(filter(lambda p: self.is_same_ver(ver, p.ver, i), remaining_pkgs))
            if len(same_ver) == 1:
                return same_ver[0].nix_key
            elif len(same_ver) == 0:
                highest = self.get_highest_ver(remaining_pkgs).nix_key
                print(f'WARNING: Unable to decide which of nixpkgs\'s definitions {[p.nix_key for p in remaining_pkgs]}'
                      f' is best as base for {name}:{ver}. Picking {highest}')
                return highest
            remaining_pkgs = same_ver
        # In every case we should have returned by now
        raise Exception("Dude... Check yor code!")

    def get_by_nix_key(self, nix_key):
        return self.data[nix_key]

    def _unify_key(self, key) -> str:
        return key.replace('-', '').replace('_', '').lower().rstrip('0123456789')

    def exists(self, name, ver=None):
        try:
            pkg = self[self._unify_key(name)]
        except KeyError:
            return False
        if ver:
            return pkg.ver == ver
        return True
