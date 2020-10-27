from typing import Iterable

import distlib.markers
import pkg_resources
from distlib.markers import DEFAULT_CONTEXT
from packaging.version import parse, _Version
from pkg_resources._vendor.packaging.specifiers import SpecifierSet

from mach_nix.cache import cached
from mach_nix.versions import PyVer


def context(py_ver: PyVer, platform: str, system: str):
    context = DEFAULT_CONTEXT.copy()
    context.update(dict(
        platform_version='',  # remove impure platform_version
        platform_release='',  # remove impure kernel verison
        platform_system=system[0].upper() + system[1:],  # eg. Linux or Darwin
        platform_machine=platform,  # eg. x86_64
        python_version=py_ver.python_version(),
        python_full_version=py_ver.python_full_version()
    ))
    return context


class Requirement(pkg_resources.Requirement):
    def __init__(self, line, build=None):
        self.build = build
        super(Requirement, self).__init__(line)
        self.name = self.name.lower().replace('_', '-')
        #self.specs = list(self.norm_specs(self.specs))
        self.specifier = SpecifierSet(','.join(f"{op}{ver}" for op, ver in self.specs))

    def __hash__(self):
        return hash((super().__hash__(), self.build))

    # @staticmethod
    # def norm_specs(specs):
    #     # PEP 440: Compatible Release
    #     for spec in specs:
    #         if spec[0] == "~=":
    #             ver = spec[1]
    #             yield ('>=', ver)
    #             ver = parse(parse(ver).base_version)
    #             ver_as_dict = ver._version._asdict()
    #             ver_as_dict['release'] = ver_as_dict['release'][:-1] + ('*',)
    #             ver._version = _Version(**ver_as_dict)
    #             yield ('==', str(ver))
    #         else:
    #             yield spec


def filter_reqs_by_eval_marker(reqs: Iterable[Requirement], context: dict, selected_extras=None):
    # filter requirements relevant for current environment
    for req in reqs:
        if req.marker is None:
            yield req
        elif selected_extras:
            for extra in selected_extras:
                extra_context = context.copy()
                extra_context['extra'] = extra
                if distlib.markers.interpret(str(req.marker), extra_context):
                    yield req
        else:
            if distlib.markers.interpret(str(req.marker), context):
                yield req


# @cached(lambda args: tuple(args[0]) if isinstance(args[0], list) else args[0])
# def parse_reqs(strs):
#     if isinstance(strs, str):
#         strs = [strs]
#     strs = list(map(
#         lambda s: s.replace(' ', '==') if not any(op in s for op in ('==', '!=', '<=', '>=', '<', '>', '~=')) else s,
#         strs
#     ))
#     reqs = list(pkg_resources.parse_requirements(strs))
#     for req in reqs:
#         r = Requirement(str(req))
#         yield r


@cached(lambda args: tuple(args[0]) if isinstance(args[0], list) else args[0])
def parse_reqs(strs):
    lines = iter(pkg_resources.yield_lines(strs))
    for line in lines:
        if ' #' in line:
            line = line[:line.find(' #')]
        if line.endswith('\\'):
            line = line[:-2].strip()
            try:
                line += next(lines)
            except StopIteration:
                return

        # handle conda requirements
        build = None
        if not any(op in line for op in ('==', '!=', '<=', '>=', '<', '>', '~=', ';')):
            # conda spec with build like "tensorflow-base 2.0.0 gpu_py36h0ec5d1f_0"
            splitted = line.split(' ')
            if len(splitted) == 3:
                name, ver, build = splitted
                line = f"{name}=={ver}"
            # transform conda specifiers without operator like "requests 2.24.*"
            else:
                line = line.replace(' ', '==')

        yield Requirement(line, build)
