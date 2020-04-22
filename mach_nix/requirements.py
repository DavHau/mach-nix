from typing import Iterable

import distlib.markers
import pkg_resources
from distlib.markers import DEFAULT_CONTEXT
from packaging.version import parse, _Version
from pkg_resources._vendor.packaging.specifiers import SpecifierSet

from mach_nix.versions import PyVer


def context(py_ver: PyVer):
    context = DEFAULT_CONTEXT.copy()
    context.update(dict(
        platform_version='',  # remove highly impure platform_version
        python_version=py_ver.python_version(),
        python_fulle_version=py_ver.python_full_version()
    ))
    return context


class Requirement(pkg_resources.Requirement):
    def __init__(self, line):
        super(Requirement, self).__init__(line)
        self.name = self.name.lower().replace('_', '-')
        self.specs = list(self.norm_specs(self.specs))
        self.specifier = SpecifierSet(','.join(f"{op}{ver}" for op, ver in self.specs))

    @staticmethod
    def norm_specs(specs):
        # PEP 440: Compatible Release
        for spec in specs:
            if spec[0] == "~=":
                ver = spec[1]
                yield ('>=', ver)
                ver = parse(parse(ver).base_version)
                ver_as_dict = ver._version._asdict()
                ver_as_dict['release'] = ver_as_dict['release'][:-1] + ('*',)
                ver._version = _Version(**ver_as_dict)
                yield ('==', str(ver))
            else:
                yield spec


def strip_reqs_by_marker(reqs: Iterable[Requirement], context: dict):
    # filter requirements relevant for current environment
    for req in reqs:
        if req.marker:
            if distlib.markers.interpret(req.marker, context):
                yield req
        else:
            yield req


def parse_reqs(strs):
    reqs = list(pkg_resources.parse_requirements(strs))
    for req in reqs:
        r = Requirement(str(req))
        yield r
