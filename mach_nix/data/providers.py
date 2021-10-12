import fnmatch
from os import environ

import json
import platform
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from operator import itemgetter
from typing import List, Tuple, Iterable

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
    selected_extras: tuple
    provider_info: 'ProviderInfo'
    build: str = None


@dataclass
class ProviderInfo:
    provider: 'DependencyProviderBase'
    wheel_fname: str = None  # only required for wheel
    url: str = None
    hash: str = None


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
        self.py_ver_parsed = parse_ver(py_ver.python_full_version())
        self.py_ver_digits = py_ver.digits()
        self.platform = platform
        self.system = system

    @cached()
    def find_matches(self, req) -> List[Candidate]:
        all = list(self.all_candidates_sorted(req.key, req.extras, req.build))
        matching_versions = set(filter_versions([c.ver for c in all], req))
        matching_candidates = [c for c in all if c.ver in matching_versions]
        return matching_candidates

    def all_candidates_sorted(self, name, extras=None, build=None) -> Iterable[Candidate]:
        candidates = list(self.all_candidates(name, extras, build))
        candidates.sort(key=lambda c: c.ver)
        return candidates

    @property
    @abstractmethod
    def name(self):
        pass

    def get_reqs_for_extras(self, pkg_name, pkg_ver, extras):
        install_reqs_wo_extras, setup_reqs_wo_extras = self.get_pkg_reqs(pkg_name, pkg_ver)
        install_reqs_w_extras, setup_reqs_w_extras = self.get_pkg_reqs(pkg_name, pkg_ver, extras=extras)
        install_reqs = set(install_reqs_w_extras) - set(install_reqs_wo_extras)
        return list(install_reqs)

    def unify_key(self, key: str) -> str:
        return key.replace('_', '-').lower()

    @abstractmethod
    @cached()
    def get_pkg_reqs(self, candidate: Candidate) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get all requirements of a candidate for the current platform and the specified extras
        returns two lists: install_requires, setup_requires
        """
        pass

    @abstractmethod
    def all_candidates(self, name, extras=None, build=None) -> Iterable[Candidate]:
        pass

    @abstractmethod
    def deviated_version(self, pkg_name, normalized_version: Version, build):
        # returns version like originally specified by package maintainer without normalization
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

    def get_provider(self, pkg_name, pkg_version, build) -> DependencyProviderBase:
        for type, provider in self.allowed_providers_for_pkg(pkg_name).items():
            if pkg_version in (c.ver for c in provider.all_candidates(pkg_name, build=build)):
                return provider

    def get_pkg_reqs(self, c: Candidate) -> Tuple[List[Requirement], List[Requirement]]:
        for provider in self.allowed_providers_for_pkg(c.name).values():
            if c in provider.all_candidates(c.name, c.selected_extras, c.build):
                return provider.get_pkg_reqs(c)

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
                f"If it still doesn't work, there might have bene an error while building the DB.\n" \
                f"Please open an issue at: https://github.com/DavHau/mach-nix/issues/new\n"
        print(error_text, file=sys.stderr)
        exit(1)

    @cached()
    def all_candidates_sorted(self, pkg_name, extras=None, build=None) -> Iterable[Candidate]:
        # use dict as ordered set
        candidates = []
        # order by reversed preference expected
        for provider in reversed(tuple(self.allowed_providers_for_pkg(pkg_name).values())):
            candidates += list(provider.all_candidates_sorted(pkg_name, extras, build))
        if not candidates:
            self.print_error_no_versions_available(pkg_name, extras, build)
        return tuple(candidates)

    def all_candidates(self, name, extras=None, build=None) -> Iterable[Candidate]:
        return self.all_candidates_sorted(name, extras, build)

    def deviated_version(self, pkg_name, pkg_version: Version, build):
        self.get_provider(pkg_name, pkg_version, build).deviated_version(pkg_name, pkg_version, build)


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

    def get_pkg_reqs(self, c: Candidate) -> Tuple[List[Requirement], List[Requirement]]:
        if not self.nixpkgs.exists(c.name, c.ver):
            raise Exception(f"Cannot find {c.name}:{c.ver} in nixpkgs")
        install_reqs, setup_reqs = [], []
        for provider in (self.sdist_provider, self.wheel_provider):
            try:
                install_reqs, setup_reqs = provider.get_pkg_reqs(c)
            except PackageNotFound:
                pass
        return install_reqs, setup_reqs

    def all_candidates(self, pkg_name, extras=None, build=None) -> Iterable[Candidate]:
        if build:
            return []
        name = self.unify_key(pkg_name)
        if not self.nixpkgs.exists(name):
            return []
        return [Candidate(
            pkg_name,
            p.ver,
            extras,
            provider_info=ProviderInfo(self)
        ) for p in self.nixpkgs.get_all_candidates(name)]

    def deviated_version(self, pkg_name, normalized_version: Version, build):
        # not necessary for nixpkgs provider since source doesn't need to be fetched
        return str(normalized_version)


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
        maj = self.py_ver_digits[0]  # major version
        min = self.py_ver_digits[1]  # minor version
        cp_abi = f"cp{maj}{min}mu" if int(maj) == 2 else f"cp{maj}{min}m?"
        if self.system == "linux":
            self.preferred_wheels = (
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-manylinux2014_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-manylinux2010_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-manylinux1_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-manylinux_2_5_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-manylinux_2_12_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-manylinux_2_17_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-linux_{self.platform}"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-any"),
            )
        elif self.system == "darwin":
            self.preferred_wheels = (
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-any"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-macosx_\d*_\d*_universal"),
                re.compile(rf".*(py{maj}|cp{maj}){min}?[\.-].*({cp_abi}|abi3|none)-macosx_\d*_\d*_x86_64"),
            )
        else:
            raise Exception(f"Unsupported Platform {platform.system()}")

    def all_candidates(self, pkg_name, extras=None, build=None) -> List[Candidate]:
        if build:
            return []
        return [Candidate(
            w.name,
            parse_ver(w.ver),
            extras,
            provider_info=ProviderInfo(provider=self, wheel_fname=w.fn)
        ) for w in self._suitable_wheels(pkg_name)]

    def get_pkg_reqs(self, c: Candidate) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get requirements for package
        """
        reqs_raw = self._choose_wheel(c.name, c.ver).requires_dist
        if reqs_raw is None:
            reqs_raw = []
        # handle extras by evaluationg markers
        install_reqs = list(filter_reqs_by_eval_marker(parse_reqs(reqs_raw), self.context_wheel, c.selected_extras))
        return install_reqs, []

    def deviated_version(self, pkg_name, pkg_version: Version, build):
        return self._choose_wheel(pkg_name, pkg_version).ver

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
        ver = parse_ver(str(self.py_ver))
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
                    if not filter_versions([self.py_ver_parsed], parsed_py_requires[0]):
                        continue
                parsed_ver = parse_ver(ver)
                candidates[parsed_ver] = pkg_data
        return candidates

    def deviated_version(self, pkg_name, normalized_version: Version, build):
        for raw_ver in self.data[normalize_name(pkg_name)].keys():
            if parse_ver(raw_ver) == normalized_version:
                return raw_ver
        raise Exception(
            f"Something went wrong while trying to find the deviated version for {pkg_name}:{normalized_version}")

    def get_reqs_for_extras(self, pkg_name, pkg_ver: Version, extras):
        name = self.unify_key(pkg_name)
        pkg = self._get_candidates(name)[pkg_ver]
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
        if c.ver not in self._get_candidates(c.name):
            raise PackageNotFound(c.name, c.ver, self.name)
        pkg = self._get_candidates(c.name)[c.ver]
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
        requirements['install_requires'] += self.get_reqs_for_extras(c.name, c.ver, c.selected_extras)
        return requirements['install_requires'], requirements['setup_requires']

    def all_candidates(self, pkg_name, extras=None, build=None) -> Iterable[Candidate]:
        if build:
            return []
        return [Candidate(
            pkg_name,
            ver,
            extras,
            provider_info=ProviderInfo(self)
        ) for ver, pkg in self._get_candidates(pkg_name).items()]


def conda_virtual_packages():

    packages = dict(
        __glibc=environ.get("MACHNIX_GLIBC_VERSION", platform.libc_ver()[0][1]),
        __unix=0,
    )

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
        name = normalize_name(c.name)
        deviated_ver = self.deviated_version(name, c.ver, c.build)
        candidate = self.pkgs[name][deviated_ver][c.build]
        depends = list(filter(
            lambda d: d.split()[0] not in self.ignored_pkgs,
           # lambda d: d.split()[0] not in self.ignored_pkgs and not d.startswith('_'),
            candidate['depends']
            # always add optional dependencies to ensure constraints are applied
            + (candidate['constrains'] if 'constrains' in candidate else [])
        ))
        return list(parse_reqs(depends)), []

    @cached()
    def all_candidates(self, pkg_name, extras=None, build=None) -> Iterable[Candidate]:
        pkg_name = normalize_name(pkg_name)
        if pkg_name not in self.pkgs:
            return []
        candidates = []
        for ver in self.pkgs[pkg_name].keys():
            for p in self.compatible_builds(pkg_name, parse_ver(ver), build):
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
                        selected_extras=tuple(),
                        build=p['build'],
                        provider_info=ProviderInfo(
                            self,
                            url=url,
                            hash=p['sha256']
                        )
                    ))
                    if 'collisions' in p:
                        print(
                            f"WARNING: Colliding conda package in channel '{self.channel}' "
                            f"Ignoring {list(map(itemgetter(0), p['collisions']))} "
                            f"from {list(map(itemgetter(1), p['collisions']))} "
                            f"in favor of {p['name']} from '{p['subdir']}'")
        return candidates

    def deviated_version(self, pkg_name, normalized_version: Version, build):
        for builds in self.pkgs[pkg_name].values():
            for p in builds.values():
                if parse_ver(p['version']) == normalized_version:
                    return p['version']
        raise Exception(f"Cannot find deviated version for {pkg_name}:{normalized_version}")

    def python_ok(self, build):
        for dep in build['depends']:
            if dep == "pypy" or dep.startswith("pypy "):
                return False
            if dep.startswith("python "):
                req = next(iter(parse_reqs([dep])))
                if not filter_versions([self.py_ver_parsed], req):
                    return False
        return True

    @cached()
    def compatible_builds(self, pkg_name, pkg_version: Version, build=None) -> list:
        deviated_ver = self.deviated_version(pkg_name, pkg_version, build)
        if build:
            matched = set(fnmatch.filter(self.pkgs[pkg_name][deviated_ver], build))
            pkgs = \
                [p for p in self.pkgs[pkg_name][deviated_ver].values() if p['build'] in matched and self.python_ok(p)]
            pkgs.sort(key=lambda p: p['build_number'], reverse=True)
            return pkgs
        compatible = []
        for build in self.pkgs[pkg_name][deviated_ver].values():
            # continue if python incompatible
            if not self.python_ok(build):
                continue
            # python is compatible
            compatible.append(build)
        return compatible
