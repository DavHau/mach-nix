from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Iterable

from packaging.version import Version

from mach_nix.requirements import Requirement


@dataclass
class ResolvedPkg:
    name: str
    ver: Version
    build_inputs: List[str]
    prop_build_inputs: List[str]
    is_root: bool


class Resolver(ABC):

    @abstractmethod
    def resolve(self, reqs: Iterable[Requirement]) -> List[ResolvedPkg]:
        pass
