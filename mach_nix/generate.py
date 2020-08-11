import json
import os
import sys
from os.path import dirname
from pprint import pformat
from typing import List

from resolvelib import ResolutionImpossible
from resolvelib.resolvers import RequirementInformation

import mach_nix
from mach_nix.data.nixpkgs import NixpkgsIndex
from mach_nix.data.providers import CombinedDependencyProvider, ProviderSettings
from mach_nix.generators.overides_generator import OverridesGenerator
from mach_nix.requirements import parse_reqs, filter_reqs_by_eval_marker, context
from mach_nix.resolver.resolvelib_resolver import ResolvelibResolver
from mach_nix.versions import PyVer


def load_env(name, *args, **kwargs):
    var = os.environ.get(name, *args, **kwargs)
    if var is None:
        print(f'Error: env variable "{name}" must not be empty', file=sys.stderr)
        exit(1)
    return var.strip()


def main():
    providers_json = load_env('providers')

    disable_checks = load_env('disable_checks')
    nixpkgs_json = load_env('nixpkgs_json')
    out_file = load_env('out_file')
    provider_settings = ProviderSettings(providers_json)
    py_ver_str = load_env('py_ver_str')
    pypi_deps_db_src = load_env('pypi_deps_db_src')
    pypi_fetcher_commit = load_env('pypi_fetcher_commit')
    pypi_fetcher_sha256 = load_env('pypi_fetcher_sha256')
    requirements = load_env('requirements')

    platform, system = load_env('system').split('-')

    py_ver = PyVer(py_ver_str)
    nixpkgs = NixpkgsIndex(nixpkgs_json)
    deps_provider = CombinedDependencyProvider(
        nixpkgs=nixpkgs,
        provider_settings=provider_settings,
        pypi_deps_db_src=pypi_deps_db_src,
        py_ver=py_ver,
        platform=platform,
        system=system
    )
    generator = OverridesGenerator(
        py_ver,
        nixpkgs,
        pypi_fetcher_commit,
        pypi_fetcher_sha256,
        disable_checks,
        ResolvelibResolver(nixpkgs, deps_provider),
    )
    reqs = filter_reqs_by_eval_marker(parse_reqs(requirements), context(py_ver, platform, system))
    try:
        expr = generator.generate(reqs)
    except ResolutionImpossible as e:
        handle_resolution_impossible(e, requirements, providers_json, py_ver_str)
        exit(1)
    else:
        with open(out_file, 'w') as f:
            f.write(expr)


def handle_resolution_impossible(exc: ResolutionImpossible, reqs_str, providers_json, py_ver_str):
    causes: List[RequirementInformation] = exc.causes
    causes_str = ''
    for ri in causes:
        causes_str += f"\n  {ri.requirement}"
        if ri.parent:
            causes_str += \
                f" - parent: {ri.parent.name}{ri.parent.extras if ri.parent.extras else ''}:{ri.parent.ver}"
    nl = '\n'
    print(
        f"\nSome requirements could not be resolved.\n"
        f"Top level requirements: \n  {'  '.join(l for l in reqs_str.splitlines())}\n"
        f"Providers:\n  {f'{nl}  '.join(pformat(json.loads(providers_json)).splitlines())}\n"
        f"Mach-nix version: {open(dirname(mach_nix.__file__) + '/VERSION').read().strip()}\n"
        f"Python: {py_ver_str}\n"
        f"Cause: {exc.__context__}\n"
        f"The requirements which caused the error:"
        f"{causes_str}\n",
        file=sys.stderr)


if __name__ == "__main__":
    main()
