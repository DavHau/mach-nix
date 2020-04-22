import os
import sys

from mach_nix.data.data_interface import NixpkgsDirectory, DependencyDB
from mach_nix.generators.overlay_generator import OverlaysGenerator
from mach_nix.requirements import parse_reqs
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
    nixpkgs_commit = load_env('nixpkgs_commit')
    nixpkgs_tarball_sha256 = load_env('nixpkgs_tarball_sha256')
    nixpkgs_json = load_env('nixpkgs_json')
    out_file = load_env('out_file')
    py_ver_str = load_env('py_ver_str')
    prefer_nixpkgs = load_env('prefer_nixpkgs')
    pypi_deps_db_data_dir = load_env('pypi_deps_db_data_dir')
    pypi_fetcher_commit = load_env('pypi_fetcher_commit')
    pypi_fetcher_tarball_sha256 = load_env('pypi_fetcher_tarball_sha256')
    requirements = load_env('requirements')

    py_ver = PyVer(py_ver_str)
    nixpkgs = NixpkgsDirectory(nixpkgs_json)
    deps_db = DependencyDB(py_ver, pypi_deps_db_data_dir)
    generator = OverlaysGenerator(
        py_ver,
        nixpkgs_commit,
        nixpkgs_tarball_sha256,
        nixpkgs,
        pypi_fetcher_commit,
        pypi_fetcher_tarball_sha256,
        disable_checks,
        ResolvelibResolver(nixpkgs, deps_db),
        prefer_nixpkgs=prefer_nixpkgs,
    )
    reqs = parse_reqs(requirements)
    expr = generator.generate(reqs)
    with open(out_file, 'w') as f:
        f.write(expr)


if __name__ == "__main__":
    main()
