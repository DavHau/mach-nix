import json
import platform
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Iterable

import distlib.markers
from packaging.version import Version, parse
from pkg_resources import RequirementParseError

from .nixpkgs import NixpkgsIndex
from mach_nix.requirements import filter_reqs_by_eval_marker, Requirement, parse_reqs, context
from mach_nix.versions import PyVer, ver_sort_key, filter_versions
from .bucket_dict import LazyBucketDict
from ..cache import cached


@dataclass
class ProviderInfo:
    provider: 'DependencyProviderBase'
    # following args are only required in case of wheel
    wheel_fname: str = None


def unify_key(key: str) -> str:
    return key.replace('_', '-').lower()


class ProviderSettings:
    def __init__(self, json_str):
        data = json.loads(json_str)
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
            return tuple(unify_key(p.strip()) for p in str_or_list.strip().split(','))
        elif isinstance(str_or_list, list):
            return tuple(unify_key(k) for k in str_or_list)
        else:
            raise Exception("Provider specifiers must be lists or comma separated strings")

    def provider_names_for_pkg(self, pkg_name):
        name = unify_key(pkg_name)
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
        self.py_ver_digits = py_ver.digits()
        self.platform = platform
        self.system = system

    @cached()
    def available_versions(self, pkg_name: str) -> Iterable[Version]:
        """
        returns available versions for given package name in reversed preference
        """
        return sorted(self._available_versions(pkg_name), key=ver_sort_key)

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
    def get_provider_info(self, pkg_name, pkg_version) -> ProviderInfo:
        """
        returns info about a candidate by it's provider.
        This is later needed to identify the origin of a package and how to retrieve it
        """
        pass

    @abstractmethod
    @cached()
    def get_pkg_reqs(self, pkg_name, pkg_version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get all requirements of a candidate for the current platform and the specified extras
        """
        pass

    @abstractmethod
    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        pass

    @abstractmethod
    def deviated_version(self, pkg_name, normalized_version: Version):
        # returns version like originally specified by package maintainer without normalization
        pass


class CombinedDependencyProvider(DependencyProviderBase):
    name = 'combined'

    def __init__(
            self,
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

    def get_provider(self, pkg_name, pkg_version) -> DependencyProviderBase:
        for type, provider in self.allowed_providers_for_pkg(pkg_name).items():
            if pkg_version in provider.available_versions(pkg_name):
                return provider

    def get_provider_info(self, pkg_name, pkg_version) -> ProviderInfo:
        return self.get_provider(pkg_name, pkg_version).get_provider_info(pkg_name, pkg_version)

    def get_pkg_reqs(self, pkg_name, pkg_version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        for provider in self.allowed_providers_for_pkg(pkg_name).values():
            if pkg_version in provider.available_versions(pkg_name):
                return provider.get_pkg_reqs(pkg_name, pkg_version, extras=extras)

    def list_all_providers_for_pkg(self, pkg_name):
        result = []
        for p_name, provider in self._all_providers.items():
            if provider.available_versions(pkg_name):
                result.append(p_name)
        return result

    def print_error_no_versions_available(self, pkg_name):
        provider_names = set(self.allowed_providers_for_pkg(pkg_name).keys())
        error_text = \
            f"\nThe Package '{pkg_name}' is not available from any of the selected providers\n" \
            f"{provider_names} for the selected python version."
        if provider_names != set(self._all_providers.keys()):
            alternative_providers = self.list_all_providers_for_pkg(pkg_name)
            if alternative_providers:
                error_text += f'\nThe package is is available from providers {alternative_providers}\n' \
                              f"Consider adding them via 'providers='."
        else:
            error_text += \
                f"\nIf the package's initial release date predates the release date of mach-nix,\n" \
                f"either upgrade mach-nix itself or set 'pypiDataRev' and 'pypiDataSha256'\n" \
                f"to a more recent commit of https://github.com/DavHau/pypi-deps-db/commits/master\n" \
                f"when importing mach-nix.\n" \
                f"If it still doesn't work, there was probably a problem while crawling pypi.\n" \
                f"Please open an issue at: https://github.com/DavHau/mach-nix/issues/new\n"
        print(error_text, file=sys.stderr)
        exit(1)

    @cached()
    def available_versions(self, pkg_name: str) -> Iterable[Version]:
        # use dict as ordered set
        available_versions = []
        # order by reversed preference expected
        for provider in reversed(tuple(self.allowed_providers_for_pkg(pkg_name).values())):
            for ver in provider.available_versions(pkg_name):
                available_versions.append(ver)
        if available_versions:
            return tuple(available_versions)
        self.print_error_no_versions_available(pkg_name)

    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        return self.available_versions(pkg_name)

    def deviated_version(self, pkg_name, pkg_version: Version):
        self.get_provider(pkg_name, pkg_version).deviated_version(pkg_name, pkg_version)


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

    def get_provider_info(self, pkg_name, pkg_version) -> ProviderInfo:
        return ProviderInfo(self)

    def get_pkg_reqs(self, pkg_name, pkg_version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        name = self.unify_key(pkg_name)
        if not self.nixpkgs.exists(name, pkg_version):
            raise Exception(f"Cannot find {name}:{pkg_version} in nixpkgs")
        install_reqs, setup_reqs = [], []
        for provider in (self.sdist_provider, self.wheel_provider):
            try:
                install_reqs, setup_reqs = provider.get_pkg_reqs(pkg_name, pkg_version, extras=extras)
            except PackageNotFound:
                pass
        return install_reqs, setup_reqs

    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        name = self.unify_key(pkg_name)
        if self.nixpkgs.exists(name):
            return [p.ver for p in self.nixpkgs.get_all_candidates(name)]
        return []

    def deviated_version(self, pkg_name, normalized_version: Version):
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

    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        return (parse(wheel.ver) for wheel in self._suitable_wheels(pkg_name))

    def get_pkg_reqs(self, pkg_name, pkg_version: Version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get requirements for package
        """
        reqs_raw = self._choose_wheel(pkg_name, pkg_version).requires_dist
        if reqs_raw is None:
            reqs_raw = []
        # handle extras by evaluationg markers
        install_reqs = list(filter_reqs_by_eval_marker(parse_reqs(reqs_raw), self.context_wheel, extras))
        return install_reqs, []

    def get_provider_info(self, pkg_name, pkg_version) -> ProviderInfo:
        wheel = self._choose_wheel(pkg_name, pkg_version)
        return ProviderInfo(provider=self, wheel_fname=wheel.fn)

    def deviated_version(self, pkg_name, pkg_version: Version):
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
            wheels = filter(lambda w: parse(w.ver) == ver, wheels)
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
        ver = parse('.'.join(self.py_ver_digits))
        try:
            parsed_py_requires = list(parse_reqs(f"python{wheel.requires_python}"))
            return bool(filter_versions([ver], parsed_py_requires[0].specs))
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
                pyver = pyvers[self.py_ver_digits]
                if isinstance(pyver, str):
                    candidates[parse(ver)] = pyvers[pyver]
                else:
                    candidates[parse(ver)] = pyvers[self.py_ver_digits]
        return candidates

    def deviated_version(self, pkg_name, normalized_version: Version):
        for raw_ver in self.data[unify_key(pkg_name)].keys():
            if parse(raw_ver) == normalized_version:
                return raw_ver
        raise Exception(
            f"Something went wrong while trying to find the deviated version for {pkg_name}:{normalized_version}")

    def get_provider_info(self, pkg_name, pkg_version):
        return ProviderInfo(provider=self)

    def get_reqs_for_extras(self, pkg_name, pkg_ver, extras):
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

    def get_pkg_reqs(self, pkg_name, pkg_version: Version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get requirements for package
        """
        if pkg_version not in self._get_candidates(pkg_name):
            raise PackageNotFound(pkg_name, pkg_version, self.name)
        pkg = self._get_candidates(pkg_name)[pkg_version]
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
        if not extras:
            extras = []
        # even if no extras are selected we need to collect reqs for extras,
        # because some extras consist of only a marker which needs to be evaluated
        requirements['install_requires'] += self.get_reqs_for_extras(pkg_name, pkg_version, extras)
        return requirements['install_requires'], requirements['setup_requires']

    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        return [ver for ver in self._get_candidates(pkg_name).keys()]

