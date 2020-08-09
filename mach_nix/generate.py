import os
import sys

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
    disable_checks = load_env('disable_checks')
    nixpkgs_json = load_env('nixpkgs_json')
    out_file = load_env('out_file')
    provider_settings = ProviderSettings(load_env('providers'))
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
    expr = generator.generate(reqs)
    with open(out_file, 'w') as f:
        f.write(expr)


if __name__ == "__main__":
    main()
