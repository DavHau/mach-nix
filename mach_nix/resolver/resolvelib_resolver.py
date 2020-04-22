from dataclasses import dataclass
from typing import Iterable, List

import resolvelib
from packaging.version import Version

from mach_nix.data.data_interface import NixpkgsDirectory, DependencyDB
from mach_nix.requirements import Requirement
from mach_nix.resolver import Resolver, ResolvedPkg
from mach_nix.versions import filter_versions, ver_sort_key


@dataclass
class Candidate:
    name: str
    ver: Version
    extras: tuple


# Implement logic so the resolver understands the requirement format.
class Provider:
    def __init__(self, nixpkgs: NixpkgsDirectory, deps_db: DependencyDB, prefer_nixpkgs: bool):
        self.prefer_nixpkgs = prefer_nixpkgs
        self.nixpkgs = nixpkgs
        self.deps_db = deps_db

    def get_extras_for(self, dependency):
        return tuple(sorted(dependency.extras))

    def get_base_requirement(self, candidate):
        return Requirement("{}=={}".format(candidate.name, candidate.ver))

    def identify(self, dependency):
        return dependency.name

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def sort_key(self, name, ver):
        key = ver_sort_key(ver)
        if self.prefer_nixpkgs and self.nixpkgs.exists(name, ver):
            return (1, *key)
        return (0, *key)

    def find_matches(self, req):
        all = self.deps_db.available_versions(req.key)

        def sort_key(ver):
            return self.sort_key(req.key, ver)
        version_matches = sorted(filter_versions(all, req.specs), key=lambda x: sort_key(x))
        return [Candidate(name=req.name, ver=ver, extras=req.extras) for ver in version_matches]

    def is_satisfied_by(self, requirement, candidate):
        if not set(requirement.extras).issubset(set(candidate.extras)):
            return False
        return bool(len(list(filter_versions([candidate.ver], requirement.specs))))

    def get_dependencies(self, candidate):
        install_requires, setup_requires = self.deps_db.get_pkg_reqs(candidate.name, candidate.ver, candidate.extras)
        deps = install_requires + setup_requires
        return deps


class ResolvelibResolver(Resolver):
    def __init__(self, nixpkgs: NixpkgsDirectory, deps_db: DependencyDB):
        self.nixpkgs = nixpkgs
        self.deps_db = deps_db

    def resolve(self,
                reqs: Iterable[Requirement],
                prefer_nixpkgs=True) -> List[ResolvedPkg]:
        reporter = resolvelib.BaseReporter()
        result = resolvelib.Resolver(Provider(self.nixpkgs, self.deps_db, prefer_nixpkgs=prefer_nixpkgs),
                                     reporter).resolve(reqs)
        nix_py_pkgs = []
        for name in result.graph._forwards.keys():
            if name is None:
                continue
            ver = result.mapping[name].ver
            install_requires, setup_requires = self.deps_db.get_pkg_reqs(name, ver)
            prop_build_inputs = list({req.key for req in install_requires}) + list(result.mapping[name].extras)
            build_inputs = list({req.key for req in setup_requires})
            is_root = name in result.graph._forwards[None]
            nix_py_pkgs.append(ResolvedPkg(
                name=name,
                ver=ver,
                build_inputs=build_inputs,
                prop_build_inputs=prop_build_inputs,
                is_root=is_root
            ))
        return nix_py_pkgs
