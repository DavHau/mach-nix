from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Iterable, Optional

from packaging.version import Version

from mach_nix.data.providers import ProviderInfo
from mach_nix.requirements import Requirement


@dataclass
class ResolvedPkg:
    name: str
    ver: Version
    build_inputs: List[str]
    prop_build_inputs: List[str]
    is_root: bool
    provider_info: ProviderInfo
    extras_selected: List[str]
    removed_circular_deps: List[str] = field(default_factory=list)


class Resolver(ABC):

    @abstractmethod
    def resolve(self, reqs: Iterable[Requirement]) -> List[ResolvedPkg]:
        pass
