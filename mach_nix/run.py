import json
import os
import subprocess as sp
import sys
import tempfile
from argparse import ArgumentParser
from os.path import realpath, dirname, isfile
from textwrap import dedent
from urllib import request
from urllib.error import HTTPError

import toml

from mach_nix.ensure_nix import ensure_nix
from mach_nix.versions import PyVer

pwd = dirname(realpath(__file__))


def gen(args, nixpkgs_rev, nixpkgs_sha256, return_expr=False):
    with open(args.r) as f:
        requirements = f.read().strip()
    o_file = tempfile.mktemp()
    py_ver = PyVer(args.python)

    cmd = f'nix-build {pwd}/nix/call_mach.nix -o {o_file}' \
          f' --argstr requirements "{requirements}"' \
          f' --argstr python_attr python{py_ver.digits()}' \
          f' --argstr nixpkgs_rev {nixpkgs_rev}' \
          f' --argstr nixpkgs_sha {nixpkgs_sha256}'
    proc = sp.run(cmd, shell=True, stdout=sys.stderr)
    if proc.returncode:
        exit(1)
    with open(f"{o_file}/share/mach_nix_file.nix") as src:
        expr = src.read()
        if return_expr:
            return expr
        if getattr(args, 'o', None):
            with open(args.o, 'w') as dest:
                dest.write(expr)
                print(f"Expression written to {args.o}")
        else:
            print(expr)


def env(args, nixpkgs_ref):
    target_dir = args.directory
    py_ver = PyVer(args.python)

    default_nix_file = f"{target_dir}/default.nix"
    inputs_nix_file = f"{target_dir}/inputs.nix"
    lock_file = f"{target_dir}/lock.toml"
    python_nix_file = f"{target_dir}/python.nix"
    requirements_file = f"{target_dir}/requirements.txt"
    shell_nix_file = f"{target_dir}/shell.nix"

    machnix_version = os.environ.get("MACHNIX_VERSION", default=None)
    if machnix_version is None:
        with open(f"{pwd}/VERSION") as f:
            machnix_version = f.read()

    with open(args.r) as f:
        requirements = f.read().strip()

    inputs_nix_content = dedent(f"""
        with builtins;
        let
          lock = fromTOML (readFile ./lock.toml);
        in rec {{
          pkgs = import (builtins.fetchTarball {{
            name = "nixpkgs";
            url = "https://github.com/nixos/nixpkgs/tarball/${{lock.nixpkgs.rev}}";
            sha256 = "${{lock.nixpkgs.sha256}}";
          }}) {{ config = {{}}; overlays = []; }};
          mach-nix = import (builtins.fetchTarball {{
            url = "https://github.com/DavHau/mach-nix/tarball/${{lock.mach-nix.rev}}";
            sha256 = lock.mach-nix.sha256;
          }}) {{
            python = "{py_ver.nix()}";
            inherit pkgs;
          }};
        }}
    """)
    python_nix_content = dedent(f"""
        with (import ./inputs.nix);
        mach-nix.mkPython {{
          requirements = builtins.readFile ./requirements.txt;
        }}
    """)
    shell_nix_content = dedent(f"""
        with (import ./inputs.nix);
        pkgs.mkShell {{
          buildInputs = [
            (import ./python.nix)
            mach-nix.mach-nix
          ];
        }}
    """)
    # ensure target path exists
    if not os.path.isdir(target_dir):
        if os.path.exists(target_dir):
            print(f'Error: {target_dir} already exists and is not a directory!')
            exit(1)
        os.mkdir(target_dir)
    # update lock file if mach-nix version mismatch
    update_lock_file(lock_file, 'DavHau', "mach-nix", machnix_version)
    update_lock_file(lock_file, 'nixos', "nixpkgs", nixpkgs_ref)

    # write requirements file
    with open(default_nix_file, 'w') as default:
        default.write("import ./shell.nix\n")
    with open(inputs_nix_file, 'w') as default:
        default.write(inputs_nix_content)
    with open(python_nix_file, 'w') as python:
        python.write(python_nix_content)
    with open(requirements_file, "w") as dest:
        dest.write(requirements)
    with open(shell_nix_file, 'w') as shell:
        shell.write(shell_nix_content)

    class c:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    print(f"\nInitialized python environment in:                {c.OKCYAN}{target_dir}{c.ENDC}\n"
          f"To change python requirements, modify the file:   {c.OKCYAN}{requirements_file}{c.ENDC}\n\n"
          f"To activate the environment, execute:             {c.BOLD}{c.OKGREEN}nix-shell {target_dir}{c.ENDC}")


def update_lock_file(file, owner, project, ref):
    lock = {}
    lock_ok = False
    if isfile(file):
        with open(file) as f:
            lock = toml.load(f)
        if project in lock\
                and all(k in lock[project] for k in ("ref", "rev", "sha256")) \
                and lock[project]['ref'].split('/')[-1] == ref:
            lock_ok = True
    if not lock_ok:
        rev, sha256 = github_rev_and_sha256(owner, project, ref)
        lock[project] = dict(
            ref=ref,
            rev=rev,
            sha256=sha256)
        with open(file, 'w') as f:
            toml.dump(lock, f)


def github_rev_and_sha256(owner, repo, ref):
    try:
        res = request.urlopen(f"https://api.github.com/repos/{owner}/{repo}/commits/{ref}").read()
    except HTTPError as e:
        print(f"Error receiving {repo} revision for {ref}: {e.msg}")
        exit(1)
    commit = json.loads(res)['sha']
    proc = sp.run(
        f"nix-prefetch-url --unpack https://github.com/{owner}/{repo}/tarball/{commit}",
        shell=True, check=True, stdout=sp.PIPE)
    sha256 = proc.stdout.decode().strip()
    return commit, sha256


def parse_args(parser: ArgumentParser, nixpkgs_ref):
    common_arguments = (
        (('-p', '--python'), dict(
            help='select python version (default: 3.7)',
            choices=('2.7', '3.5', '3.6', '3.7', '3.8'),
            default='3.7')),

        (('-r',), dict(
            help='path to requirements.txt file',
            metavar='requirements.txt',
            required=True)),

        (('--nixpkgs',), dict(
            help=dedent('select nixpkgs revision. Can be a branch or tag or revision'),
            default=nixpkgs_ref,
            required=False, )),
    )
    parser.add_argument('--version', '-V', help='show program version', action='store_true')
    subparsers = parser.add_subparsers(dest='command')

    gen_parser = subparsers.add_parser('gen', help='generate a nix expression')
    gen_parser.add_argument('-o', help='output file. defaults to stdout', metavar='python.nix')

    env_parser = subparsers.add_parser('env', help='set up a venv-style environment')
    env_parser.add_argument('directory', help='target directory to create the environment')

    for p in (gen_parser, env_parser):
        for args, kwargs in common_arguments:
            p.add_argument(*args, **kwargs)

    return parser.parse_args()


def main():
    # read nixpkgs json file for revision ref
    flakes_lock = f"""{pwd}/flake.lock"""
    with open(flakes_lock, 'r') as f:
        nixpkgs_ref = json.load(f)['nodes']['nixpkgs']['locked']['rev']

    parser = ArgumentParser()
    args = parse_args(parser, nixpkgs_ref)

    if args.version:
        with open(f"{pwd}/VERSION") as f:
            print(f.read())
            exit(0)

    if args.command not in ('gen', 'env'):
        parser.print_usage()
        exit(1)

    ensure_nix()

    if args.command == 'gen':
        gen(args, *github_rev_and_sha256('nixos', 'nixpkgs', args.nixpkgs))
    elif args.command == 'env':
        env(args, nixpkgs_ref=args.nixpkgs)


if __name__ == "__main__":
    main()
