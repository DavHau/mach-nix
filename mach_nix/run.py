import json
import os
import subprocess as sp
import sys
import tempfile
from argparse import ArgumentParser
from os.path import realpath, dirname

from mach_nix.ensure_nix import ensure_nix
from mach_nix.versions import PyVer


pwd = dirname(realpath(__file__))


def gen(args, return_expr=False):
    with open(args.r) as f:
        requirements = f.read().strip()
    o_file = tempfile.mktemp()
    py_ver = PyVer(args.python)
    cmd = f'nix-build {pwd}/nix/expression.nix -o {o_file}' \
          f' --argstr requirements "{requirements}"' \
          f' --argstr python_attr python{py_ver.digits()}' \
          f' --arg prefer_nixpkgs {json.dumps((not args.prefer_new))}'
    proc = sp.run(cmd, shell=True, stdout=sys.stderr)
    if proc.returncode:
        print(proc.stderr.decode(), file=sys.stderr)
        exit(1)
    with open(f"{o_file}/share/expr.nix") as src:
        expr = src.read()
        if return_expr:
            return expr
        if getattr(args, 'o', None):
            with open(args.o, 'w') as dest:
                dest.write(expr)
                print(f"Expression written to {args.o}")
        else:
            print(expr)


def env(args):
    target_dir = args.directory
    expr = gen(args, return_expr=True)
    python_nix_file = f"{target_dir}/python.nix"
    shell_nix_file = f"{target_dir}/shell.nix"
    default_nix_file = f"{target_dir}/default.nix"
    if not os.path.isdir(target_dir):
        if os.path.exists(target_dir):
            print(f'Error: {target_dir} already exists and is not a directory!')
            exit(1)
        os.mkdir(target_dir)
    with open(python_nix_file, 'w') as python:
        with open(shell_nix_file, 'w') as shell:
            with open(default_nix_file, 'w') as default:
                python.write(expr)
                shell.write("(import ./python.nix).env\n")
                default.write("import ./shell.nix\n")
    print(f"\nInitialized python environment in {target_dir}\n"
          f"To activate it, execute: 'nix-shell {target_dir}'")


def print_be_patient():
    print("Generating python environment... If you run this the first time, the python package index "
          "and dependency graph (~200MB) need to be downloaded. Please stay patient!", file=sys.stderr)


def main():
    common_arguments = (
        (('-p', '--python'), dict(
            help='select python version (default: 3.7)',
            choices=('2.7', '3.5', '3.6', '3.7', '3.8'),
            default='3.7')),

        (('-r',), dict(
            help='path to requirements.txt file',
            metavar='requirements.txt',
            required=True)),

        (('--prefer-new',), dict(
            action='store_true',
            help='Prefer newer python package versions instead of the ones from nixpkgs. '
                 'This might increase build times significantly since no cache can be used'))
    )
    parser = ArgumentParser()
    parser.add_argument('--version', '-V', help='show program version', action='store_true')
    subparsers = parser.add_subparsers(dest='command')

    gen_parser = subparsers.add_parser('gen', help='generate a nix expression')
    gen_parser.add_argument('-o', help='output file. defaults to stdout', metavar='python.nix')

    env_parser = subparsers.add_parser('env', help='set up a venv-style environment')
    env_parser.add_argument('directory', help='target directory to create the environment')

    for p in (gen_parser, env_parser):
        for args, kwargs in common_arguments:
            p.add_argument(*args, **kwargs)

    args = parser.parse_args()

    if args.version:
        with open(f"{pwd}/VERSION") as f:
            print(f"mach-nix: {f.read()}")
            exit(0)

    if args.command not in ('gen', 'env'):
        parser.print_usage()
        exit(1)

    ensure_nix()
    print_be_patient()

    if args.command == 'gen':
        gen(args)
    elif args.command == 'env':
        env(args)


if __name__ == "__main__":
    main()
