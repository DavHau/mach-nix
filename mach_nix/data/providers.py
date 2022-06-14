import fnmatch
from os import environ

import json
import platform
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from operator import itemgetter
from typing import Any, Iterable, List, Optional, Tuple

import distlib.markers
from pkg_resources import RequirementParseError

from mach_nix.requirements import filter_reqs_by_eval_marker, Requirement, parse_reqs, context, filter_versions
from mach_nix.versions import PyVer, parse_ver, Version
from .bucket_dict import LazyBucketDict
from .nixpkgs import NixpkgsIndex
from ..cache import cached


@dataclass
class Candidate:
    name: str
    ver: Version
    raw_version: str
    selected_extras: tuple
    provider_info: 'ProviderInfo'
    build: str = None


@dataclass
class ProviderInfo:
    provider: 'DependencyProviderBase'
    wheel_fname: str = None  # only required for wheel
    url: str = None
    hash: str = None
    data: Any = None  # Provider specific data

    def toDict(self):
        return dict(
            provider=self.provider.name,
            wheel_fname=self.wheel_fname,
            url=self.url,
            hash=self.hash,
        )


def normalize_name(key: str) -> str:
    return key.replace('_', '-').lower()


class ProviderSettings:
    def __init__(self, providers_json):
        with open(providers_json) as f:
            data = json.load(f)
        if isinstance(data, list) or isinstance(data, str):
            self.default_providers = self._parse_provider_list(data)
            self.pkg_providers = {}
        elif isinstance(data, dict):
            if '_default' not in data:
                raise Exception("Providers must contain '_default' key")
            self.pkg_providers = {k: self._parse_provider_list(v) for k, v in data.items()}
            self.default_providers = self.pkg_providers['_default']
            del self.pkg_providers['_default']
        else:
            raise Exception('Wrong format for provider settings')

    def _parse_provider_list(self, str_or_list) -> Tuple[str]:
        if isinstance(str_or_list, str):
            return tuple(normalize_name(p.strip()) for p in str_or_list.strip().split(','))
        elif isinstance(str_or_list, list):
            return tuple(normalize_name(k) for k in str_or_list)
        else:
            raise Exception("Provider specifiers must be lists or comma separated strings")

    def provider_names_for_pkg(self, pkg_name):
        name = normalize_name(pkg_name)
        if name in self.pkg_providers:
            return self.pkg_providers[name]
        else:
            return self.default_providers


class PackageNotFound(Exception):
    def __init__(self, pkg_name, pkg_ver, provider_name, *args, **kwargs):
        super(PackageNotFound, self).__init__(f"Provider '{provider_name}' cannot provide {pkg_name}:{pkg_ver}")


class DependencyProviderBase(ABC):
    def __init__(self, py_ver: PyVer, platform, system, *args, **kwargs):
        self.context = context(py_ver, platform, system)
        self.context_wheel = self.context.copy()
        self.context_wheel['extra'] = None
        self.py_ver = py_ver
        self.py_ver_digits = py_ver.digits()
        self.platform = platform
        self.system = system

    @cached(keyfunc=lambda args: (args[0], tuple(args[1])))
    def find_matches(self, reqs) -> List[Candidate]:
        extras = tuple({extra for req in reqs for extra in req.extras})
        builds = tuple({req.build for req in reqs if req.build is not None})
        all = list(self.all_candidates_sorted(reqs[0].key, extras, builds))
        matching_versions = [c.ver for c in all]
        for req in reqs:
            matching_versions = filter_versions(matching_versions, req)
        matching_versions = set(matching_versions)
        matching_candidates = [c for c in all if c.ver in matching_versions]
        return matching_candidates

    def all_candidates_sorted(self, name, extras, builds) -> Iterable[Candidate]:
        candidates = list(self.all_candidates(name, extras, builds))
        candidates.sort(key=lambda c: c.ver, reverse=True)
        return candidates

    @property
    @abstractmethod
    def name(self):
        pass

    def unify_key(self, key: str) -> str:
        return key.replace('_', '-').lower()

    @abstractmethod
    @cached()
    def get_pkg_reqs(self, candidate: Candidate) -> Tuple[Optional[List[Requirement]], Optional[List[Requirement]]]:
        """
        Get all requirements of a candidate for the current platform and the specified extras
        returns two lists: install_requires, setup_requires
        """
        pass

    @abstractmethod
    def all_candidates(self, name, extras, builds) -> Iterable[Candidate]:
        pass


class CombinedDependencyProvider(DependencyProviderBase):
    name = 'combined'

    def __init__(
            self,
            conda_channels_json,
            nixpkgs: NixpkgsIndex,
            provider_settings: ProviderSettings,
            pypi_deps_db_src: str,
            *args,
            **kwargs):
        super(CombinedDependencyProvider, self).__init__(*args, **kwargs)
        self.provider_settings = provider_settings
        wheel = WheelDependencyProvider(f"{pypi_deps_db_src}/wheel", *args, **kwargs)
        sdist = SdistDependencyProvider(f"{pypi_deps_db_src}/sdist", *args, **kwargs)
        nixpkgs = NixpkgsDependencyProvider(nixpkgs, wheel, sdist, *args, **kwargs)
        self._all_providers = {
            f"{wheel.name}": wheel,
            f"{sdist.name}": sdist,
            f"{nixpkgs.name}": nixpkgs,
        }
        with open(conda_channels_json) as f:
            self._all_providers.update({
                f"conda/{channel_name}": CondaDependencyProvider(channel_name, files, *args, **kwargs)
                for channel_name, files in json.load(f).items()
            })
        providers_used = set(provider_settings.default_providers)
        for p_list in provider_settings.pkg_providers.values():
            for p in p_list:
                providers_used.add(p)
        unknown_providers = providers_used - set(self._all_providers.keys())
        if unknown_providers:
            raise Exception(f"Error: Unknown providers '{unknown_providers}'. Please remove from 'providers=...'")

    def allowed_providers_for_pkg(self, pkg_name):
        provider_keys = self.provider_settings.provider_names_for_pkg(pkg_name)
        selected_providers = ((name, p) for name, p in self._all_providers.items() if name in provider_keys)
        return dict(sorted(selected_providers, key=lambda x: provider_keys.index(x[0])))

    def get_pkg_reqs(self, c: Candidate) -> Tuple[Optional[List[Requirement]], Optional[List[Requirement]]]:
        return c.provider_info.provider.get_pkg_reqs(c)

    def list_all_providers_for_pkg(self, pkg_name, extras, build):
        result = []
        for p_name, provider in self._all_providers.items():
            if provider.all_candidates(pkg_name, extras, build):
                result.append(p_name)
        return result

    def print_error_no_versions_available(self, pkg_name, extras, build):
        provider_names = set(self.allowed_providers_for_pkg(pkg_name).keys())
        error_text = \
            f"\nThe Package '{pkg_name}' (build: {build}) is not available from any of the " \
            f"selected providers {sorted(provider_names)}\n for the selected python version"
        if provider_names != set(self._all_providers.keys()):
            alternative_providers = self.list_all_providers_for_pkg(pkg_name, extras, build)
            if alternative_providers:
                error_text += \
                    f'\nThe package is is available from providers {alternative_providers}\n' \
                    f"Consider adding them via 'providers='."
        else:
            error_text += \
                f"\nThe required package might just not (yet) be part of the dependency DB currently used.\n" \
                f"The DB can be updated by specifying 'pypiDataRev' when importing mach-nix.\n" \
                f"For examples see: https://github.com/DavHau/mach-nix/blob/master/examples.md\n" \
                f"If it still doesn't work, there might have been an error while building the DB.\n" \
                f"Please open an issue at: https://github.com/DavHau/mach-nix/issues/new\n"
        print(error_text, file=sys.stderr)
        exit(1)

    @cached()
    def all_candidates_sorted(self, pkg_name, extras, builds) -> Iterable[Candidate]:
        # use dict as ordered set
        candidates = []
        # order by reversed preference expected
        for provider in tuple(self.allowed_providers_for_pkg(pkg_name).values()):
            candidates += list(provider.all_candidates_sorted(pkg_name, extras, builds))
        if not candidates:
            self.print_error_no_versions_available(pkg_name, extras, builds)
        return tuple(candidates)

    def all_candidates(self, name, extras, builds) -> Iterable[Candidate]:
        return self.all_candidates_sorted(name, extras, builds)


class NixpkgsDependencyProvider(DependencyProviderBase):
    name = 'nixpkgs'

    # TODO: implement extras by looking them up via the equivalent wheel
    def __init__(
            self,
            nixpkgs: NixpkgsIndex,
            wheel_provider: 'WheelDependencyProvider',
            sdist_provider: 'SdistDependencyProvider',
            *args, **kwargs):
        super(NixpkgsDependencyProvider, self).__init__(*args, **kwargs)
        self.nixpkgs = nixpkgs
        self.wheel_provider = wheel_provider
        self.sdist_provider = sdist_provider

    def get_pkg_reqs(self, c: Candidate) -> Tuple[Optional[List[Requirement]], Optional[List[Requirement]]]:
        requirements = self.nixpkgs.get_requirements(c.name, c.ver)
        if requirements is not None:
            return list(parse_reqs(requirements)), None

        for provider in (self.sdist_provider, self.wheel_provider):
            candidates = [
                candidate
                for candidate in provider.all_candidates(c.name, None, None)
                if candidate.ver == c.ver
            ]
            if len(candidates) > 0:
                return provider.get_pkg_reqs(candidates[0])
        return None, None

    def all_candidates(self, pkg_name, extras, builds) -> Iterable[Candidate]:
        if builds:
            return []
        name = self.unify_key(pkg_name)
        if not self.nixpkgs.exists(name):
            return []
        return [Candidate(
            pkg_name,
            p.ver,
            str(p.ver),
            extras,
            provider_info=ProviderInfo(self)
        ) for p in self.nixpkgs.get_all_candidates(name)]


@dataclass
class WheelRelease:
    fn_pyver: str  # the python version indicated by the filename
    name: str
    ver: str
    fn: str
    requires_dist: list
    provided_extras: list
    requires_python: str  # the python version of the wheel metadata

    def __hash__(self):
        return hash(self.fn)


class WheelDependencyProvider(DependencyProviderBase):
    name = 'wheel'
    def __init__(self, data_dir: str, *args, **kwargs):
        super(WheelDependencyProvider, self).__init__(*args, **kwargs)
        self.data = LazyBucketDict(data_dir)
        maj = self.py_ver.version.release[0]  # major version
        min = self.py_ver.version.release[1]  # minor version
        cp_abi = f"cp{maj}{min}mu" if int(maj) == 2 else f"cp{maj}{min}m?"
        if self.system == "linux":
            self.preferred_wheels = (
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-manylinux2014_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-manylinux2010_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-manylinux1_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-manylinux_2_5_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-manylinux_2_12_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-manylinux_2_17_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-linux_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-any"),
            )
        elif self.system == "darwin":
            platform = "arm64" if self.platform == "aarch64" else self.platform
            self.preferred_wheels = (
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-any"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-macosx_\d*_\d*_universal"),
                re.compile(rf".*(py{maj}|cp{maj})({min})?[\.-].*({cp_abi}|abi3|none)-macosx_\d*_\d*_{platform}"),
            )
        else:
            raise Exception(f"Unsupported Platform {platform.system()}")

    def all_candidates(self, pkg_name, extras, builds) -> List[Candidate]:
        if builds:
            return []
        return [Candidate(
            w.name,
            parse_ver(w.ver),
            w.ver,
            extras,
            provider_info=ProviderInfo(provider=self, wheel_fname=w.fn, data=w)
        ) for w in self._suitable_wheels(pkg_name)]

    def get_pkg_reqs(self, c: Candidate) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get requirements for package
        """
        reqs_raw = c.provider_info.data.requires_dist
        if reqs_raw is None:
            reqs_raw = []
        # handle extras by evaluationg markers
        install_reqs = list(filter_reqs_by_eval_marker(parse_reqs(reqs_raw), self.context_wheel, c.selected_extras))
        return install_reqs, []

    def _all_releases(self, pkg_name):
        name = self.unify_key(pkg_name)
        if name not in self.data:
            return []
        for fn_pyver, vers in self.data[name].items():
            for ver, fnames in vers.items():
                for fn, deps in fnames.items():
                    if isinstance(deps, str):
                        key_ver, key_fn = deps.split('@')
                        versions = self.data[name][fn_pyver]
                        deps = versions[key_ver][key_fn]
                    assert isinstance(deps, dict)
                    yield WheelRelease(
                        fn_pyver,
                        name,
                        ver,
                        fn,
                        deps['requires_dist'] if 'requires_dist' in deps else None,
                        deps['requires_extras'] if 'requires_extras' in deps else None,
                        deps['requires_python'].strip(',') if 'requires_python' in deps else None,
                    )

    def _apply_filters(self, filters: List[callable], objects: Iterable):
        """
        Applies multiple filters to objects. First filter in the list is applied first
        """
        assert len(filters) > 0
        if len(filters) == 1:
            return filter(filters[0], objects)
        return filter(filters[-1], self._apply_filters(filters[:-1], objects))

    @cached()
    def _choose_wheel(self, pkg_name, pkg_version: Version) -> WheelRelease:
        suitable = list(self._suitable_wheels(pkg_name, pkg_version))
        if not suitable:
            raise PackageNotFound(pkg_name, pkg_version, self.name)
        return self._select_preferred_wheel(suitable)

    def _suitable_wheels(self, pkg_name: str, ver: Version = None) -> Iterable[WheelRelease]:
        wheels = self._all_releases(pkg_name)
        if ver is not None:
            wheels = filter(lambda w: parse_ver(w.ver) == ver, wheels)
        return self._apply_filters(
            [
                self._wheel_type_ok,
                self._python_requires_ok,
            ],
            wheels)

    def _select_preferred_wheel(self, wheels: Iterable[WheelRelease]):
        wheels = list(wheels)
        for pattern in self.preferred_wheels:
            for wheel in wheels:
                if re.search(pattern, wheel.fn):
                    return wheel
        raise Exception(f"No wheel type found that is compatible to the current system")

    def _wheel_type_ok(self, wheel: WheelRelease):
        return any(re.search(pattern, wheel.fn) for pattern in self.preferred_wheels)

    def _python_requires_ok(self, wheel: WheelRelease):
        if not wheel.requires_python:
            return True
        ver = self.py_ver.version
        try:
            parsed_py_requires = list(parse_reqs(f"python{wheel.requires_python}"))
            return bool(filter_versions([ver], parsed_py_requires[0]))
        except RequirementParseError:
            print(f"WARNING: `requires_python` attribute of wheel {wheel.name}:{wheel.ver} could not be parsed")
            return False


class SdistDependencyProvider(DependencyProviderBase):
    name = 'sdist'

    def __init__(self, data_dir: str, *args, **kwargs):
        self.data = LazyBucketDict(data_dir)
        super(SdistDependencyProvider, self).__init__(*args, **kwargs)

    @cached()
    def _get_candidates(self, name) -> dict:
        """
        returns all candidates for the give name which are available for the current python version
        """
        key = self.unify_key(name)
        candidates = {}
        try:
            self.data[key]
        except KeyError:
            return {}
        for ver, pyvers in self.data[key].items():
            # in case pyvers is a string, it is a reference to another ver which we need to resolve
            if isinstance(pyvers, str):
                pyvers = self.data[key][pyvers]
            # in case pyver is a string, it is a reference to another pyver which we need to resolve
            if self.py_ver_digits in pyvers:
                pkg_data = pyvers[self.py_ver_digits]
                if isinstance(pkg_data, str):
                    pkg_data = pyvers[pkg_data]
                if 'python_requires' in pkg_data:
                    specs = ",".join(pkg_data['python_requires'])
                    parsed_py_requires = list(parse_reqs(f"python{specs}"))
                    if not filter_versions([self.py_ver.version], parsed_py_requires[0]):
                        continue
                candidates[ver] = pkg_data
        return candidates

    def _get_reqs_for_extras(self, pkg, extras):
        if extras is None:
            return []
        extras = set(extras)
        requirements = []
        if 'extras_require' in pkg:
            for name, reqs_str in pkg['extras_require'].items():
                # handle extras with marker in key
                if ':' in name:
                    name, marker = name.split(':')
                    if not distlib.markers.interpret(marker, self.context):
                        continue
                if name == '' or name in extras:
                    requirements += list(filter_reqs_by_eval_marker(parse_reqs(reqs_str), self.context))
        return requirements

    def get_pkg_reqs(self, c: Candidate) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get requirements for package
        """
        pkg = c.provider_info.data
        requirements = dict(
            setup_requires=[],
            install_requires=[]
        )
        for t in ("setup_requires", "install_requires"):
            if t not in pkg:
                requirements[t] = []
            else:
                reqs_raw = pkg[t]
                reqs = parse_reqs(reqs_raw)
                requirements[t] = list(filter_reqs_by_eval_marker(reqs, self.context))
        # even if no extras are selected we need to collect reqs for extras,
        # because some extras consist of only a marker which needs to be evaluated
        requirements['install_requires'] += self._get_reqs_for_extras(pkg, c.selected_extras)
        return requirements['install_requires'], requirements['setup_requires']

    def all_candidates(self, pkg_name, extras, builds) -> Iterable[Candidate]:
        if builds:
            return []
        return [Candidate(
            pkg_name,
            parse_ver(ver),
            ver,
            extras,
            provider_info=ProviderInfo(self, data=pkg)
        ) for ver, pkg in self._get_candidates(pkg_name).items()]


def conda_virtual_packages():

    packages = dict(
        __unix=0,
    )

    # platform.libc_ver() returns ('', '') on macOS and MACHNIX_GLIBC_VERSION is unset
    libc_complier, libc_version = platform.libc_ver()
    if libc_complier == 'glibc':
        packages['__glibc'] = environ.get("MACHNIX_GLIBC_VERSION", libc_version)

    # Maximum version of CUDA supported by the display driver.
    cudaVer = environ.get("MACHNIX_CUDA_VERSION", None)
    if cudaVer is not None:
        packages['__cuda'] = cudaVer

    if sys.platform == 'linux':
        packages['__linux'] = environ.get("MACHNIX_LINUX_VERSION", platform.uname().release)

    if sys.platform == 'darwin':
        packages['__osx'] = environ.get("MACHNIX_OSX_VERSION", platform.uname().release)

    return packages


class CondaDependencyProvider(DependencyProviderBase):

    ignored_pkgs = (
        "python"
    )

    virtual_packages = conda_virtual_packages()

    def __init__(self, channel, files, py_ver: PyVer, platform, system, *args, **kwargs):
        self.channel = channel
        self.pkgs = {}
        for file in files:
            with open(file) as f:
                content = json.load(f)
            for i, fname in enumerate(content['packages'].keys()):
                p = content['packages'][fname]
                name = p['name'].replace('_', '-').lower()
                ver = p['version']
                build = p['build']
                if name not in self.pkgs:
                    self.pkgs[name] = {}
                if ver not in self.pkgs[name]:
                    self.pkgs[name][ver] = {}
                if build in self.pkgs[name][ver]:
                    if 'collisions' not in self.pkgs[name][ver][build]:
                        self.pkgs[name][ver][build]['collisions'] = []
                    self.pkgs[name][ver][build]['collisions'].append((p['name'], p['subdir']))
                    continue
                self.pkgs[name][ver][build] = p
                self.pkgs[name][ver][build]['fname'] = fname

        # generate packages for virtual packages
        for pname, ver in self.virtual_packages.items():
            pname_norm = pname.replace('_', '-').lower()
            self.pkgs[pname_norm] = {ver: {0: {
                'build': 0,
                'build_number': 0,
                'depends': [],
                'fname': None,
                'name': pname_norm,
                'sha256': None,
                'subdir': None,
                'version': ver,
            }}}

        super().__init__(py_ver, platform, system, *args, **kwargs)

    @property
    def name(self):
        return f"conda/{self.channel}"

    def get_pkg_reqs(self, c: Candidate) -> Tuple[List[Requirement], List[Requirement]]:
        candidate = c.provider_info.data
        depends = list(filter(
            lambda d: d.split()[0] not in self.ignored_pkgs,
            # lambda d: d.split()[0] not in self.ignored_pkgs and not d.startswith('_'),
            candidate['depends']
            # always add optional dependencies to ensure constraints are applied
            + (candidate['constrains'] if 'constrains' in candidate else [])
        ))
        return list(parse_reqs(depends)), []

    @cached()
    def all_candidates_sorted(self, name, extras, build) -> Iterable[Candidate]:
        candidates = self.all_candidates(name, extras, build)
        candidates.sort(
            key=lambda c: (c.ver, c.provider_info.data["build_number"]),
            reverse=True,
        )
        return candidates


    def all_candidates(self, pkg_name, extras, builds) -> Iterable[Candidate]:
        pkg_name = normalize_name(pkg_name)
        if pkg_name not in self.pkgs:
            return []
        candidates = []
        for p in self.compatible_builds(pkg_name, builds):
            if 'sha256' not in p:
                print(
                    f"Ignoring conda package {p['name']}:{p['version']} from provider {self.channel} \n"
                    "since it doesn't provide a sha256 sum.\n")
            else:
                if self.channel in ('free', 'intel', 'main', 'r'):
                    url = f"https://repo.anaconda.com/pkgs/{self.channel}/{p['subdir']}/{p['fname']}"
                else:
                    url = f"https://anaconda.org/{self.channel}/{p['name']}/" \
                          f"{p['version']}/download/{p['subdir']}/{p['fname']}"
                candidates.append(Candidate(
                    p['name'],
                    parse_ver(p['version']),
                        p['version'],
                    selected_extras=tuple(),
                    build=p['build'],
                    provider_info=ProviderInfo(
                        self,
                        url=url,
                        hash=p['sha256'],
                        data=p,
                    )
                ))
                if 'collisions' in p:
                    print(
                        f"WARNING: Colliding conda package in channel '{self.channel}' "
                        f"Ignoring {list(map(itemgetter(0), p['collisions']))} "
                        f"from {list(map(itemgetter(1), p['collisions']))} "
                        f"in favor of {p['name']} from '{p['subdir']}'")
        return candidates

    def python_ok(self, build):
        for dep in build['depends']:
            if dep == "pypy" or dep.startswith("pypy "):
                return False
            if dep.startswith("python "):
                req = next(iter(parse_reqs([dep])))
                if not filter_versions([self.py_ver.version], req):
                    return False
        return True

    @cached()
    def compatible_builds(self, pkg_name, build_patterns) -> list:
        if build_patterns:
            # fnmatch caches the regexes it builds.
            def build_matches(build):
                return all((fnmatch.fnmatch(build, build_pattern) for build_pattern in build_patterns))
        else:
            def build_matches(build):
                return True
        return [
            pkg_data
            for ver, pkg_builds in self.pkgs[pkg_name].items()
            for build, pkg_data in pkg_builds.items()
            if self.python_ok(pkg_data)
            and build_matches(build)
        ]
