import json
from collections import UserDict
from dataclasses import dataclass
from typing import List

from mach_nix.cache import cached
from mach_nix.versions import parse_ver, Version


@dataclass
class NixpkgsPyPkg:
    name: str
    nix_key: str
    ver: Version


class NixpkgsIndex(UserDict):
    # mapping from pypi name to nix key
    _aliases = dict(
        torch='pytorch',
    )

    def __init__(self, nixpkgs_json_file, **kwargs):
        with open(nixpkgs_json_file) as f:
            data = json.load(f)
        self.data = {}
        self.requirements = {}
        for nix_key, nix_data in data.items():
            if nix_data is None:
                continue
            pname = nix_data["pname"]
            raw_version = nix_data["version"]
            try:
                version = parse_ver(raw_version)
            except ValueError:
                version = raw_version
            pname_key = pname.replace("_", "-").lower()
            if pname_key not in self.data:
                self.data[pname_key] = {}
            if version not in self.data[pname_key]:
                self.data[pname_key][version] = []
            self.data[pname_key][version].append(nix_key)
            if nix_data["requirements"] is not None:
                self.requirements[nix_key] = nix_data["requirements"]
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
            result += [NixpkgsPyPkg(name, nix_key, ver) for nix_key in nix_keys]
        return result

    def get_highest_ver(self, pkgs: List[NixpkgsPyPkg]):
        # prioritizing similar names, reduces chance of infinite recursion
        # (see problem with dateutil alias)
        name_difference = lambda p: abs(len(p.name)-len(p.nix_key))
        return max(pkgs, key=lambda p: (p.ver, -name_difference(p)))

    @staticmethod
    def is_same_ver(ver1, ver2, prefix_len):
        """
        Check if the given versions share a common prefix of length `prefix_len`.

        This ignores any epoch or pre/post-release versions. For the epoch,
        it is likely that the nixpkg version doesn't include the epoch, and
        just has the release version.
        """
        def prefix(ver):
            # Return a version prefix of the given length, padded with 0s.
            return ver.release[:prefix_len] + (0,) * max(0, prefix_len - len(ver.release))
        return prefix(ver1) == prefix(ver2)

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
        for i in range(1, len(ver.release)):
            same_ver = list(filter(lambda p: self.is_same_ver(ver, p.ver, i), remaining_pkgs))
            if len(same_ver) == 1:
                return same_ver[0].nix_key
            elif len(same_ver) == 0:
                # If there are no versions that match at this precision
                # we pick the best version among the version that matched
                # at the prior prefix.
                break
            remaining_pkgs = same_ver
        # We've either fallen off the loop (in which case the versions match)
        # or all remaining packages match the same length version prefix.
        highest = self.get_highest_ver(remaining_pkgs).nix_key
        print(f'Multiple nixpkgs attributes found for {name}-{ver}: {[p.nix_key for p in remaining_pkgs]}'
              f"\nPicking '{highest}' as base attribute name.")
        return highest

    def exists(self, name, ver=None):
        try:
            candidates = [c for c in self.get_all_candidates(name)]
        except KeyError:
            return False
        if ver:
            return any(ver == c.ver for c in candidates)
        return True

    def get_requirements(self, name, ver):
        nix_key = self.find_best_nixpkgs_candidate(name, ver)
        return self.requirements.get(nix_key)
