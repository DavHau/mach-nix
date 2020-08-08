import json
import os
import subprocess as sp
import tempfile
from os.path import realpath, dirname
from time import time

import toml

from mach_nix.generate import main

pwd = dirname(realpath(__file__))

os.environ['py_ver_str'] = '3.7.5'
os.environ['system'] = 'x86_64-linux'
os.environ['out_file'] = f'{pwd}/overrides.nix'
os.environ['disable_checks'] = 'true'

with open(pwd + "/../mach_nix/provider_defaults.toml") as f:
    provider_settings = toml.load(f)
if os.path.isfile("./providers.toml"):
    with open(pwd + "./providers.toml") as f:
        provider_settings.update(toml.load(f))
provider_settings.update(dict(
    # add providers here
))
os.environ['providers'] = json.dumps(provider_settings)

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

with open(pwd + "/reqs.txt") as f:
    os.environ['requirements'] = f.read()

# generates and writes nix expression into ./debug/expr.nix
start = time()
main()
dur = round(time() - start, 1)
print(f"resolving took: {dur}s")
