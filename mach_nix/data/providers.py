import json
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Iterable, Set

import distlib.markers
from packaging.version import Version, parse

from .nixpkgs import NixpkgsDirectory
from mach_nix.requirements import filter_reqs_by_eval_marker, Requirement, parse_reqs, context
from mach_nix.versions import PyVer, ver_sort_key
from .bucket_dict import LazyBucketDict


@dataclass
class ProviderInfo:
    provider: str
    # following args are only required in case of wheel
    wheel_pyver: str = None
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
    def __init__(self, py_ver: PyVer, *args, **kwargs):
        self.context = context(py_ver)
        self.context_wheel = self.context.copy()
        self.context_wheel['extra'] = None
        self.py_ver_digits = py_ver.digits()

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
    def get_pkg_reqs(self, pkg_name, pkg_version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get all requirements of a candidate for the current platform and the specified extras
        """
        pass

    @abstractmethod
    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        pass


class CombinedDependencyProvider(DependencyProviderBase):
    name = 'combined'

    def __init__(self,
                 nixpkgs: NixpkgsDirectory,
                 prefer_new: bool,
                 provider_settings: ProviderSettings,
                 pypi_deps_db_src: str,
                 *args,
                 **kwargs):
        super(CombinedDependencyProvider, self).__init__(*args, **kwargs)
        self.prefer_new = prefer_new
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

    def providers_for_pkg(self, pkg_name):
        provider_keys = self.provider_settings.provider_names_for_pkg(pkg_name)
        selected_providers = ((name, p) for name, p in self._all_providers.items() if name in provider_keys)
        return dict(sorted(selected_providers, key=lambda x: provider_keys.index(x[0])))

    def get_provider_info(self, pkg_name, pkg_version) -> ProviderInfo:
        for type, provider in self.providers_for_pkg(pkg_name).items():
            if pkg_version in provider.available_versions(pkg_name):
                return provider.get_provider_info(pkg_name, pkg_version)

    def get_pkg_reqs(self, pkg_name, pkg_version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        for provider in self.providers_for_pkg(pkg_name).values():
            if pkg_version in provider.available_versions(pkg_name):
                return provider.get_pkg_reqs(pkg_name, pkg_version, extras=extras)

    def list_providers_for_pkg(self, pkg_name):
        result = []
        for p_name, provider in self._all_providers.items():
            if provider.available_versions(pkg_name):
                result.append(p_name)
        return result

    def print_error_no_versions_available(self, pkg_name):
        provider_names = set(self.providers_for_pkg(pkg_name).keys())
        error_text = f"\nThe Package '{pkg_name}' is not available from any of the " \
                     f"selected providers {provider_names}\n for the selected python version"
        if provider_names != set(self._all_providers.keys()):
            alternative_providers = self.list_providers_for_pkg(pkg_name)
            if alternative_providers:
                error_text += f'... but the package is is available from providers {alternative_providers}\n' \
                              f"Consider adding them via 'providers='"
        else:
            error_text += \
                f"\nIf the package's initial release date predates the release date of mach-nix, " \
                f"either upgrade mach-nix itself or manually specify 'pypi_deps_db_commit' and\n" \
                f"'pypi_deps_db_sha256 for a newer commit of https://github.com/DavHau/pypi-deps-db/commits/master\n" \
                f"If it still doesn't work, there was probably a problem while extracting dependency information " \
                f"by the crawler maintaining the database.\n" \
                f"Please open an issue here: https://github.com/DavHau/pypi-crawlers/issues/new\n"
        print(error_text, file=sys.stderr)
        exit(1)

    def available_versions(self, pkg_name: str) -> Iterable[Version]:
        # use dict as ordered set
        available_versions = []
        # order by reversed preference expected
        for provider in reversed(tuple(self.providers_for_pkg(pkg_name).values())):
            for ver in provider.available_versions(pkg_name):
                available_versions.append(ver)
        if available_versions:
            if self.prefer_new:
                return tuple(sorted(available_versions, key=ver_sort_key))
            return tuple(available_versions)
        self.print_error_no_versions_available(pkg_name)

    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        return self.available_versions(pkg_name)


class NixpkgsDependencyProvider(DependencyProviderBase):
    name = 'nixpkgs'
    # mapping from pypi name to nix key
    # _aliases = dict(
    #     torch='pytorch',
    #     tensorboard='tensorflow-tensorboard'
    # )

    # TODO: implement extras by looking them up via the equivalent wheel
    def __init__(self,
                 nixpkgs: NixpkgsDirectory,
                 wheel_provider: 'WheelDependencyProvider',
                 sdist_provider: 'SdistDependencyProvider',
                 *args, **kwargs):
        super(NixpkgsDependencyProvider, self).__init__(*args, **kwargs)
        self.nixpkgs = nixpkgs
        self.wheel_provider = wheel_provider
        self.sdist_provider = sdist_provider

    def get_provider_info(self, pkg_name, pkg_version) -> ProviderInfo:
        return ProviderInfo(self.name)

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

    # def unify_key(self, key: str) -> str:
    #     key = super(NixpkgsDependencyProvider, self).unify_key(key)
    #     if key in self._aliases:
    #         return self._aliases[key]
    #     return key


class WheelDependencyProvider(DependencyProviderBase):
    name = 'wheel'

    def __init__(self, data_dir: str, *args, **kwargs):
        super(WheelDependencyProvider, self).__init__(*args, **kwargs)
        self.data = LazyBucketDict(data_dir)
        major, minor = self.py_ver_digits
        self.py_ver_re = re.compile(rf"^(py|cp)?{major}\.?{minor}?$")
        self.preferred_wheels = (
            'manylinux2014_x86_64.whl',
            'manylinux2010_x86_64.whl',
            'manylinux1_x86_64.whl',
            'none-any.whl'
        )

    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        name = self.unify_key(pkg_name)
        result = []
        for pyver in self._get_pyvers_for_pkg(name):
            vers = self.data[name][pyver]
            for ver, fnames in vers.items():
                for fn, deps in fnames.items():
                    if self._wheel_ok(fn):
                        result.append(parse(ver))
                        break
        return result


    def choose_wheel(self, pkg_name, pkg_version: Version) -> Tuple[str, str]:
        name = self.unify_key(pkg_name)
        ver = str(pkg_version)
        ok_fnames = {}
        for pyver in self._get_pyvers_for_pkg(name):
            if not ver in self.data[name][pyver]:
                continue
            fnames = self.data[name][pyver][ver]
            ok_fnames = {fn: pyver for fn in fnames if
                         self._wheel_ok(fn) and any(fn.endswith(end) for end in self.preferred_wheels)}
        if not ok_fnames:
            raise Exception(f"No wheel available for {name}:{ver}")
        if len(ok_fnames) > 1:
            fn = self._select_preferred_wheel(ok_fnames)
            print(f"WARNING: multiple wheels available for {name}:{ver}:\n"
                  f"    {ok_fnames}\n"
                  f"Picking: {fn}")
        else:
            fn = list(ok_fnames.keys())[0]
        pyver = ok_fnames[fn]
        return pyver, fn

    def get_provider_info(self, pkg_name, pkg_version) -> ProviderInfo:
        wheel_pyver, wheel_fname = self.choose_wheel(pkg_name, pkg_version)
        return ProviderInfo(provider=self.name, wheel_pyver=wheel_pyver, wheel_fname=wheel_fname)

    def get_pkg_reqs_raw(self, pkg_name, pkg_version: Version):
        name = self.unify_key(pkg_name)
        if pkg_version not in self._available_versions(pkg_name):
            raise PackageNotFound(pkg_name, pkg_version, self.name)
        ver = str(pkg_version)
        pyver, fn = self.choose_wheel(pkg_name, pkg_version)
        deps = self.data[name][pyver][ver][fn]
        if isinstance(deps, str):
            key_ver, key_fn = deps.split('@')
            versions = self.data[name][pyver]
            deps = versions[key_ver][key_fn]
        return deps['requires_dist'] if 'requires_dist' in deps else []

    def get_pkg_reqs(self, pkg_name, pkg_version: Version, extras=None) -> Tuple[List[Requirement], List[Requirement]]:
        """
        Get requirements for package
        """
        reqs_raw = self.get_pkg_reqs_raw(pkg_name, pkg_version)
        # handle extras by evaluationg markers
        install_reqs = list(filter_reqs_by_eval_marker(parse_reqs(reqs_raw), self.context_wheel, extras))
        return install_reqs, []

    def _get_pyvers_for_pkg(self, name) -> Iterable:
        name = self.unify_key(name)
        if name not in self.data:
            return []
        ok_pyvers = (pyver for pyver in self.data[name].keys() if self._pyver_ok(pyver))
        return ok_pyvers

    def _select_preferred_wheel(self, filenames: Iterable[str]):
        for key in self.preferred_wheels:
            for fn in filenames:
                if fn.endswith(key):
                    return fn
        raise Exception("No wheel matches expected format")

    def _pyver_ok(self, ver: str):
        ver = ver.strip()
        major, minor = self.py_ver_digits
        if re.fullmatch(self.py_ver_re, ver) \
                or ver == f"py{major}"\
                or ver == "py2.py3":
            return True
        return False

    def _wheel_ok(self, fn):
        if fn.endswith('any.whl'):
            return True
        elif "manylinux" in fn:
            return True


class SdistDependencyProvider(DependencyProviderBase):
    name = 'sdist'
    def __init__(self, data_dir: str, *args, **kwargs):
        self.data = LazyBucketDict(data_dir)
        super(SdistDependencyProvider, self).__init__(*args, **kwargs)

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

    def get_provider_info(self, pkg_name, pkg_version):
        return ProviderInfo(provider=self.name)

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
        if extras:
            requirements['install_requires'] += self.get_reqs_for_extras(pkg_name, pkg_version, extras)
        return requirements['install_requires'], requirements['setup_requires']

    def _available_versions(self, pkg_name: str) -> Iterable[Version]:
        return [ver for ver in self._get_candidates(pkg_name).keys()]

