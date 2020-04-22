import json
import os
import subprocess as sp
import sys
import tempfile
import urllib
from argparse import ArgumentParser
from os.path import realpath, dirname
from urllib.request import urlretrieve

from mach_nix.versions import PyVer


def ensure_nix():
    nix_installed = True
    try:
        sp.run(['nix', '--version'], check=True, capture_output=True)
    except FileNotFoundError:
        nix_installed = False
    if nix_installed:
        return
    print("The nix package manager is required! Install it now? [Y/n]: ", end='')
    answer = input()
    if not answer or answer[0].lower() != 'y':
        exit(1)
    with urllib.request.urlopen('https://nixos.org/nix/install') as f:
        install_script = f.read()
    read, write = os.pipe()
    os.write(write, install_script)
    os.close(write)
    proc = sp.run('sh', stdin=read)
    if proc.returncode:
        print("Error while installing nix. Please check https://nixos.org/download.html and install manually.",
              file=sys.stderr)
        exit(1)


def gen(args, quiet: bool, return_expr=False):
    with open(args.r) as f:
        requirements = f.read().strip()
    pwd = dirname(realpath(__file__))
    o_file = tempfile.mktemp()
    py_ver = PyVer(args.python)
    cmd = f'nix-build {pwd}/nix/expression.nix -o {o_file}' \
          f' --argstr requirements "{requirements}"' \
          f' --argstr python_attr python{py_ver.digits()}' \
          f' --arg prefer_nixpkgs {json.dumps((not args.prefer_new))}'
    proc = sp.run(cmd, shell=True, capture_output=quiet)
    if proc.returncode:
        if quiet:
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
    expr = gen(args, quiet=False, return_expr=True)
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
    print(f"created files: {python_nix_file}, {shell_nix_file}")


def main():
    parser = ArgumentParser()
    parser.add_argument('-p', '--python', help='select python version (default: 3.7)',
                        choices=('2.7', '3.5', '3.6', '3.7', '3.8'), default='3.7')
    parser.add_argument('-r', help='path to requirements.txt file', metavar='requirements.txt', required=True)
    subparsers = parser.add_subparsers(dest='command', required=True)
    parser.add_argument('--prefer-new', action='store_true',
                        help='Prefer newer python package versions instead of the ones from nixpkgs. '
                             'This might increase build times significantly since no cache can be used',)

    gen_parser = subparsers.add_parser('gen', help='generate a nix expression')
    gen_parser.add_argument('-o', help='output file. defaults to stdout')

    env_parser = subparsers.add_parser('env', help='set up a venv-style environment')
    env_parser.add_argument('directory', help='target directory to create the environment')

    args = parser.parse_args()

    ensure_nix()

    if args.command == 'gen':
        gen(args, quiet=not args.o)
    elif args.command == 'env':
        env(args)


if __name__ == "__main__":
    main()
