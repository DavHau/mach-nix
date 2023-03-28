import re
from typing import Iterable, Tuple, List

import distlib.markers
import pkg_resources
from distlib.markers import DEFAULT_CONTEXT
from packaging.specifiers import SpecifierSet

from mach_nix.cache import cached
from mach_nix.versions import PyVer, Version


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

re_pytz = re.compile(r"pytz>dev|pytz\(>dev\)")

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


extra_name = r"([a-z]|[A-Z]|-|_|\.|\d)+"
re_marker_extras = re.compile(rf"extra *== *'?({extra_name})'?")


def extras_from_marker(marker):
    matches = re.findall(re_marker_extras, marker)
    if matches:
        return tuple(group[0] for group in matches)
    return tuple()

re_spec_part = r"( *(==|!=|>=|<=|>|<|~=|=)? *(\* |-?\w?\d(\w|\.|\*|-|\||!|\+)*))"
re_reqs = re.compile(
    r"^(?P<name>([a-z]|[A-Z]|-|_|\d|\.)+)"
    rf"(?P<extras>\[({extra_name},?)+\])?"
    r"("
        r"("
            # conda style single spec + single build
            r" *(?P<specs_1>(\w|\.|\*|-|!|\+)+)"
            r" +(?P<build_1>([a-z]|\d|_|\*|\.)+)"
        r"|"
            # multiple specs
            r" *\(?(?P<specs_0>"
                r"\*"
                rf"|{re_spec_part}([,\|]{re_spec_part})*(?![_\d]))\)?"
            r"(?P<build_0> *([a-z]|\d|_|\*|\.)+)?"
        r"|"
            # single spec only
            r" *(?P<specs_2>(\w|\.|\*|-|!|\+)+)"
        r")"
    r")?"
    r"( *[:;] *(?P<marker>.*))?$")  # marker


def parse_reqs_line(line):
    # We special case `pytz>dev` since several packages have that requirement.
    # The intent is to accept any version, but the versioning scheme used by versions prior to 2013.6
    # were detected as pre-releases.
    # See https://github.com/pypa/pip/issues/974#issuecomment-22641489
    if line == 'pytz>dev' or line == 'pytz (>dev)':
        return ("pytz", (), (), None, None)

    line = line.split("#")[0].strip()
    if line.endswith("==*"):
        line = line[:-3]

    # Throw away direct references.
    if "@" in line:
        line = line.split("@")[0]

    # remove ' symbols
    split = line.split(';')
    if len(split) > 1:
        init, marker = split
        init = init.replace("'", "").replace('"', '')
        line = init + ';' + marker
    else:
        line = line.replace("'", "").replace('"', '')
    
    if line.endswith(','):
        line = line[:-1]

    match = re.fullmatch(re_reqs, line)
    if not match:
        raise Exception(f"couldn't parse: '{line}'")
    # groups = list(match.groups())
    name = match.group('name')

    extras = match.group('extras')
    if extras:
        extras = tuple(extras.strip('[]').split(','))
    else:
        extras = tuple()

    # extract specs and build
    for i in range(2):
        try:
            all_specs = match.group(f'specs_{i}')
            build = match.group(f'build_{i}')
            if all_specs is not None:
                break
        except IndexError:
            pass
    else:
        all_specs = match.group('specs_2')
        build = None

    if build:
        build = build.strip()

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
                parsed_parts.append(part)
            all_specs.append(SpecifierSet(",".join(parsed_parts)))

        all_specs = tuple(all_specs)

    marker = match.group('marker')
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
    if not req.specs:
        # We filter version with an empty specifier set, since that will filter
        # out prerelease, if there are any other releases.
        return list(SpecifierSet().filter(versions))
    matched_versions = []
    for specs in req.specs:
        matched_versions.extend(
            specs.filter(versions)
        )
    return matched_versions
