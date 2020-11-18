import re
from typing import Iterable

import distlib.markers
import pkg_resources
from distlib.markers import DEFAULT_CONTEXT
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
        self.specifier = SpecifierSet(','.join(f"{op}{ver}" for op, ver in self.specs))

    def __hash__(self):
        return hash((super().__hash__(), self.build))


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


all_ops = {'==', '!=', '<=', '>=', '<', '>', '~=', ';'}


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
        yield Requirement(*parse_reqs_line(line))


def parse_reqs_line(line):
    build = None
    line = line.strip(' ,')
    splitted = line.split(' ')

    # conda spec with build like "tensorflow-base 2.0.0 gpu_py36h0ec5d1f_0"
    # or "hdf5 >=1.10.5,<1.10.6.0a0 mpi_mpich_*"
    if len(splitted) == 3 \
            and not splitted[1] in all_ops \
            and not any(op in splitted[0]+splitted[2] for op in all_ops) \
            and (
                splitted[-1].isdigit()
                or (len(splitted[-1]) > 1 and splitted[-1][-2] == '_')
                or '*' in splitted[-1]
                or not any(op in splitted[1] for op in all_ops)
            ):
        name, ver_spec, build = splitted
        if not any(op in ver_spec for op in all_ops):
            ver_spec = f"=={ver_spec}"
        line = f"{name}{ver_spec}"

    # parse conda specifiers without operator like "requests 2.24.*"
    elif len(splitted) == 2:
        name, ver_spec = splitted
        if not any(op in name + ver_spec for op in all_ops):
            ver_spec = f"=={ver_spec}"
        line = f"{name}{ver_spec}"

    if build is None \
            or build == "*"\
            or re.match(r"(py)?\d+_\d+", build)\
            or re.match(r"\d+", build):
        build = None

    return line, build
