from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Iterable, Set

from mach_nix.data.providers import ProviderInfo
from mach_nix.requirements import Requirement
from mach_nix.versions import Version

from json import JSONEncoder


@dataclass
class ResolvedPkg(JSONEncoder):
    name: str
    ver: Version
    raw_version: str
    build_inputs: Optional[List[str]]
    prop_build_inputs: Optional[List[str]]
    is_root: bool
    provider_info: ProviderInfo
    extras_selected: List[str]
    # contains direct or indirect children wich have been diconnected due to circular deps
    removed_circular_deps: Set[str] = field(default_factory=set)
    build: str = None

    def toDict(self):
        return dict(
            name=self.name,
            ver=str(self.ver),
            build_inputs=self.build_inputs,
            prop_build_inputs=self.prop_build_inputs,
            is_root=self.is_root,
            provider_info=self.provider_info.toDict(),
            extras_selected=self.extras_selected,
            removed_circular_deps=list(self.removed_circular_deps),
            build=self.build,
        )


class Resolver(ABC):

    @abstractmethod
    def resolve(self, reqs: Iterable[Requirement]) -> List[ResolvedPkg]:
        pass
