import json
from collections import UserDict
from dataclasses import dataclass
from typing import List

from packaging.version import Version, parse


@dataclass
class NixpkgsPyPkg:
    nix_key: str
    ver: Version


class NixpkgsDirectory(UserDict):
    _aliases = dict(
        torch='pytorch'
    )

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

    def __getitem__(self, name) -> NixpkgsPyPkg:
        return self.data[self._unify_key(name)][-1]

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
                      f' suits best as base for {name}:{ver}. Picking {highest}')
                return highest
            remaining_pkgs = same_ver
        # In every case we should have returned by now
        raise Exception("Dude... Check yor code!")

    def get_by_nix_key(self, nix_key):
        return self.data[nix_key]

    def _unify_key(self, key) -> str:
        key = key.replace('-', '').replace('_', '').lower().rstrip('0123456789')
        if key in self._aliases:
            return self._aliases[key]
        return key

    def exists(self, name, ver=None):
        try:
            candidates = [c for c in self.get_all_candidates(name)]
        except KeyError:
            return False
        if ver:
            return any(ver == c.ver for c in candidates)
        return True