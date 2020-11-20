import re
from typing import Iterable, Tuple, List

import distlib.markers
import pkg_resources
from conda.models.version import ver_eval
from distlib.markers import DEFAULT_CONTEXT
from pkg_resources._vendor.packaging.specifiers import SpecifierSet

from mach_nix.cache import cached
from mach_nix.versions import PyVer, Version, parse_ver


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


class Requirement:
    def __init__(self, name, extras, specs: Tuple[Tuple[Tuple[str, str]]], build=None, marker=None):
        self.name = name.lower().replace('_', '-')
        self.extras = extras or tuple()
        self.specs = specs or tuple()
        self.build = build
        self.marker = marker

    def __repr__(self):
        return ' '.join(map(lambda x: str(x), filter(lambda e: e, (self.name, self.extras, self.specs, self.build, self.marker))))

    @property
    def key(self):
        return self.name

    def __hash__(self):
        return hash((self.name, self.specs, self.build))


class RequirementOld(pkg_resources.Requirement):
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


re_specs = re.compile(r"(==|!=|>=|<=|>|<|~=)(.*)")


def parse_spec_part(part):
    specs = []
    op, ver = re.fullmatch(re_specs, part.strip()).groups()
    ver = ver.strip()
    specs.append((op, ver))
    return list(specs)


extra_name = r"([a-z]|[A-Z]|-|_|\d)+"
re_marker_extras = re.compile(rf"extra *== *'?({extra_name})'?")


def extras_from_marker(marker):
    matches = re.findall(re_marker_extras, marker)
    if matches:
        return tuple(group[0] for group in matches)
    return tuple()


re_reqs = re.compile(
    r"^(([a-z]|[A-Z]|-|_|\d|\.)+)"  # name
    r"("
        rf"(\[({extra_name},?)+\])?"  # extras
        r" *\(?(([,\|]? *(==|!=|>=|<=|>|<|~=|=)? *(\* |\d(\d|\.|\*|[a-z])*))+(?![_\d]))\)?"  # specs
        r"( *([a-z]|\d|_|\*)+)?"  # build
    r")?"
    r"( *[:;] *(.*))?$")  # marker


def parse_reqs_line(line):
    match = re.fullmatch(re_reqs, line)
    if not match:
        raise Exception(f"couldn't parse: '{line}'")
    groups = list(match.groups())
    name = groups[0]

    extras = groups[3]
    if extras:
        extras = tuple(extras.strip('[]').split(','))
    else:
        extras = tuple()

    all_specs = groups[6]
    if all_specs:
        all_specs_raw = all_specs.split('|')
        all_specs = []
        for specs in all_specs_raw:
            parts = specs.split(',')
            parsed_parts = []
            for part in parts:
                if not re.search(r"==|!=|>=|<=|>|<|~=|=", part):
                    part = '==' + part
                elif re.fullmatch(r"=\d(\d|\.|\*|[a-z])*", part):
                    part = '=' + part
                parsed_parts += parse_spec_part(part)
            all_specs.append(tuple(parsed_parts))

        all_specs = tuple(all_specs)

    build = groups[11]
    if build:
        build = build.strip()

    marker = groups[14]
    if marker:
        extras_marker = extras_from_marker(marker)
        extras = extras + extras_marker

    return name, extras, all_specs, build, marker


@cached(keyfunc=lambda args: hash((tuple(args[0]), args[1])))
def filter_versions(
        versions: List[Version],
        req: Requirement):
    """
    Reduces a given list of versions to contain only versions
    which are allowed according to the given specifiers
    """
    assert isinstance(versions, list)
    versions = list(versions)
    if not req.specs:
        return versions
    all_versions = []
    for specs in req.specs:
        for op, ver in specs:
            if op == '==':
                if str(ver) == "*":
                    return versions
                elif '*' in str(ver):
                    op = '='
            ver = parse_ver(ver)
            versions = list(filter(lambda v: ver_eval(v, f"{op}{ver}"), versions))
        all_versions += list(versions)
    return all_versions