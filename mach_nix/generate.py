import os
import sys

from mach_nix.data.providers import CombinedDependencyProvider
from mach_nix.data.nixpkgs import NixpkgsDirectory
from mach_nix.generators.overlay_generator import OverlaysGenerator
from mach_nix.requirements import parse_reqs, strip_reqs_by_marker, context
from mach_nix.resolver.resolvelib_resolver import ResolvelibResolver
from mach_nix.versions import PyVer


def load_env(name, *args, **kwargs):
    var = os.environ.get(name, *args, **kwargs)
    if var is None:
        print(f'Error: env variable "{name}" must not be empty', file=sys.stderr)
        exit(1)
    return var.strip()


def load_providers(providers_str: str):
    choices = ('nixpkgs', 'sdist', 'wheel')
    providers = tuple(p.strip() for p in providers_str.split(','))
    unknown_providers = set(providers) - set(choices)
    if unknown_providers:
        raise Exception(f"Providers {unknown_providers} are unknown. Please remove them from 'providers='!")
    return providers


def main():
    disable_checks = load_env('disable_checks')
    nixpkgs_commit = load_env('nixpkgs_commit')
    nixpkgs_sha256 = load_env('nixpkgs_sha256')
    nixpkgs_json = load_env('nixpkgs_json')
    out_file = load_env('out_file')
    py_ver_str = load_env('py_ver_str')
    pypi_deps_db_src = load_env('pypi_deps_db_src')
    pypi_fetcher_commit = load_env('pypi_fetcher_commit')
    pypi_fetcher_sha256 = load_env('pypi_fetcher_sha256')
    requirements = load_env('requirements')
    providers = load_providers(load_env('providers'))

    py_ver = PyVer(py_ver_str)
    nixpkgs = NixpkgsDirectory(nixpkgs_json)
    deps_provider = CombinedDependencyProvider(
        nixpkgs=nixpkgs,
        providers=providers,
        pypi_deps_db_src=pypi_deps_db_src,
        py_ver=py_ver
    )
    generator = OverlaysGenerator(
        py_ver,
        nixpkgs_commit,
        nixpkgs_sha256,
        nixpkgs,
        pypi_fetcher_commit,
        pypi_fetcher_sha256,
        disable_checks,
        providers,
        ResolvelibResolver(nixpkgs, deps_provider),
    )
    reqs = strip_reqs_by_marker(parse_reqs(requirements), context(py_ver))
    expr = generator.generate(reqs)
    with open(out_file, 'w') as f:
        f.write(expr)


if __name__ == "__main__":
    main()
