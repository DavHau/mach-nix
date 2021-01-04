import json
from collections import UserDict
from dataclasses import dataclass
from typing import List

from packaging.version import Version, parse

from mach_nix.cache import cached


@dataclass
class NixpkgsPyPkg:
    name: str
    nix_key: str
    ver: Version


class NixpkgsIndex(UserDict):
    # mapping from pypi name to nix key
    _aliases = dict(
        torch='pytorch',
        tensorboard='tensorflow-tensorboard_2'
    )

    def __init__(self, nixpkgs_json_file, **kwargs):
        with open(nixpkgs_json_file) as f:
            data = json.load(f)
        self.data = {}
        for nix_key, s in data.items():
            if '@' not in s:
                continue
            pname, version = s.split('@')
            pname_key = pname.replace('_', '-').lower()
            if pname_key not in self.data:
                self.data[pname_key] = {}
            if version not in self.data[pname_key]:
                self.data[pname_key][version] = []
            self.data[pname_key][version].append(nix_key)
        super(NixpkgsIndex, self).__init__(self.data, **kwargs)

    def has_multiple_candidates(self, name):
        count = 0
        for nix_keys in self.data[name].values():
            count += len(nix_keys)
            if count > 1:
                return True
        return False

    def get_all_candidates(self, name) -> List[NixpkgsPyPkg]:
        result = []
        for ver, nix_keys in self.data[name].items():
            result += [NixpkgsPyPkg(name, nix_key, parse(ver)) for nix_key in nix_keys]
        return result

    def get_highest_ver(self, pkgs: List[NixpkgsPyPkg]):
        # prioritizing similar names, reduces chance of infinite recursion
        # (see problem with dateutil alias)
        name_difference = lambda p: abs(len(p.name)-len(p.nix_key))
        return max(pkgs, key=lambda p: (p.ver, -name_difference(p)))

    @staticmethod
    def is_same_ver(ver1, ver2, ver_idx):
        if any(not ver.release or len(ver.release) <= ver_idx for ver in (ver1, ver2)):
            return False
        return ver1.release[ver_idx] == ver2.release[ver_idx]

    @cached(lambda args: (args[1], args[2]))
    def find_best_nixpkgs_candidate(self, name, ver):
        """
        In case a python package has more than one candidate in nixpkgs
        like `django` and `django_2_2`, this algo will select the right one.
        """
        pkgs: List[NixpkgsPyPkg] = sorted(self.get_all_candidates(name), key=lambda pkg: pkg.ver)
        if len(pkgs) == 1:
            return pkgs[0].nix_key
        # try to find nixpkgs candidate with closest version
        remaining_pkgs = pkgs
        for i in range(7):  # usually there are not more than 4 parts in a version
            same_ver = list(filter(lambda p: self.is_same_ver(ver, p.ver, i), remaining_pkgs))
            if len(same_ver) == 1:
                return same_ver[0].nix_key
            elif len(same_ver) == 0:
                highest = self.get_highest_ver(remaining_pkgs).nix_key
                print(f'Multiple nixkgs attributes found for {name}-{ver}: {[p.nix_key for p in remaining_pkgs]}'
                      f"\nPicking '{highest}' as base attribute name.")
                return highest
            remaining_pkgs = same_ver
        # In any case we should have returned by now
        raise Exception("Dude... Check yor code!")

    def exists(self, name, ver=None):
        try:
            candidates = [c for c in self.get_all_candidates(name)]
        except KeyError:
            return False
        if ver:
            return any(ver == c.ver for c in candidates)
        return True
