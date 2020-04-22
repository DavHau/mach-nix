from abc import ABC, abstractmethod
from typing import List

from mach_nix.requirements import Requirement
from mach_nix.resolver import Resolver


class ExpressionGenerator(ABC):

    def __init__(self, resolver: Resolver):
        self.resolver = resolver

    @abstractmethod
    def generate(self, reqs: List[Requirement]) -> str:
        pass
