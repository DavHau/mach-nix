from dataclasses import dataclass
from typing import Iterable, List

import resolvelib
from packaging.version import Version

from mach_nix.data.providers import DependencyProviderBase
from mach_nix.data.nixpkgs import NixpkgsDirectory
from mach_nix.requirements import Requirement
from mach_nix.resolver import Resolver, ResolvedPkg
from mach_nix.versions import filter_versions


@dataclass
class Candidate:
    name: str
    ver: Version
    extras: tuple


# Implement logic so the resolver understands the requirement format.
class Provider:
    def __init__(self, nixpkgs: NixpkgsDirectory, deps_db: DependencyProviderBase):
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

    def find_matches(self, req):
        all = self.deps_db.available_versions(req.key)
        matching_versions = filter_versions(all, req.specs)
        return [Candidate(name=req.name, ver=ver, extras=req.extras) for ver in matching_versions]

    def is_satisfied_by(self, requirement, candidate):
        if not set(requirement.extras).issubset(set(candidate.extras)):
            return False
        return bool(len(list(filter_versions([candidate.ver], requirement.specs))))

    def get_dependencies(self, candidate):
        install_requires, setup_requires = self.deps_db.get_pkg_reqs(candidate.name, candidate.ver, candidate.extras)
        deps = install_requires + setup_requires
        return deps


class ResolvelibResolver(Resolver):
    def __init__(self, nixpkgs: NixpkgsDirectory, deps_provider: DependencyProviderBase):
        self.nixpkgs = nixpkgs
        self.deps_provider = deps_provider

    def resolve(self,
                reqs: Iterable[Requirement],
                prefer_nixpkgs=True) -> List[ResolvedPkg]:
        reporter = resolvelib.BaseReporter()
        result = resolvelib.Resolver(Provider(self.nixpkgs, self.deps_provider), reporter).resolve(reqs)
        nix_py_pkgs = []
        for name in result.graph._forwards.keys():
            if name is None:
                continue
            ver = result.mapping[name].ver
            install_requires, setup_requires = self.deps_provider.get_pkg_reqs(
                name, ver, extras=result.mapping[name].extras)
            provider_info = self.deps_provider.get_provider_info(name, ver)
            prop_build_inputs = list({req.key for req in install_requires})
            build_inputs = list({req.key for req in setup_requires})
            is_root = name in result.graph._forwards[None]
            nix_py_pkgs.append(ResolvedPkg(
                name=name,
                ver=ver,
                build_inputs=build_inputs,
                prop_build_inputs=prop_build_inputs,
                is_root=is_root,
                provider_info=provider_info,
                extras_selected=list(result.mapping[name].extras)
            ))
        return nix_py_pkgs
