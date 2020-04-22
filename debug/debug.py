import os
import subprocess as sp
import tempfile
from os.path import realpath, dirname

from mach_nix.generate import main

pwd = dirname(realpath(__file__))

os.environ['py_ver_str'] = '3.7.5'
os.environ['out_file'] = f'{pwd}/expr.nix'
os.environ['disable_checks'] = 'true'
os.environ['prefer_nixpkgs'] = 'true'

nixpkgs_json = tempfile.mktemp()
cmd = f'nix-build {pwd}/nixpkgs-json.nix -o {nixpkgs_json}'
print(cmd)
sp.check_call(cmd, shell=True)
os.environ['nixpkgs_json'] = nixpkgs_json

pypi_deps_db = tempfile.mktemp()

cmd = f'nix-build {pwd}/pypi-deps-db.nix -o {pypi_deps_db}'
sp.check_call(cmd, shell=True)
os.environ['pypi_deps_db_data_dir'] = pypi_deps_db + "/data"

for key in ('NIXPKGS_COMMIT', 'NIXPKGS_TARBALL_SHA256'):
    with open(f"{pwd}/../mach_nix/nix/{key}") as f:
        os.environ[key.lower()] = f.read()

for key in ('PYPI_FETCHER_COMMIT', 'PYPI_FETCHER_TARBALL_SHA256'):
    with open(f"{pypi_deps_db}/{key}") as f:
        os.environ[key.lower()] = f.read()

os.environ['requirements'] = 'requests'


# generates and writes nix expression into ./debug/expr.nix
main()
