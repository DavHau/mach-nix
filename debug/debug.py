import json
import os
import subprocess as sp
import tempfile
from os.path import realpath, dirname

from mach_nix.generate import main

pwd = dirname(realpath(__file__))

os.environ['py_ver_str'] = '3.6.5'
os.environ['out_file'] = f'{pwd}/overrides.nix'
os.environ['prefer_new'] = f'true'
os.environ['disable_checks'] = 'true'
os.environ['providers'] = json.dumps(dict(
    _default="nixpkgs,sdist,wheel"
))

nixpkgs_json = tempfile.mktemp()
cmd = f'nix-build {pwd}/nixpkgs-json.nix -o {nixpkgs_json}'
sp.check_call(cmd, shell=True)
os.environ['nixpkgs_json'] = nixpkgs_json

pypi_deps_db = tempfile.mktemp()
cmd = f'nix-build {pwd}/pypi-deps-db.nix -o {pypi_deps_db}'
sp.check_call(cmd, shell=True)
os.environ['pypi_deps_db_src'] = pypi_deps_db

for key in ('NIXPKGS_COMMIT', 'NIXPKGS_SHA256'):
    with open(f"{pwd}/../mach_nix/nix/{key}") as f:
        os.environ[key.lower()] = f.read()

for key in ('PYPI_FETCHER_COMMIT', 'PYPI_FETCHER_SHA256'):
    with open(f"{pypi_deps_db}/{key}") as f:
        os.environ[key.lower()] = f.read()

os.environ['requirements'] = """
requests
"""

# generates and writes nix expression into ./debug/expr.nix
main()
