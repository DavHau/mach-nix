import os
import subprocess as sp
import sys
import urllib.request


def is_nix_available():
    nix_installed = False
    try:
        sp.run(['nix', '--version'], check=True, capture_output=True)
        nix_installed = True
    except FileNotFoundError:
        pass
    return nix_installed


def ensure_nix():
    if is_nix_available():
        return
    print("The nix package manager is required! Install it now? [Y/n]: ", end='')
    try:
        answer = input()
        if not answer or answer[0].lower() != 'y':
            exit(1)
    except KeyboardInterrupt:
        exit(1)
    with urllib.request.urlopen('https://nixos.org/nix/install') as f:
        install_script = f.read()
    read, write = os.pipe()
    os.write(write, install_script)
    os.close(write)
    proc = sp.run('bash', stdin=read)
    if proc.returncode:
        print("Error while installing nix. Please check https://nixos.org/download.html for manual installation.",
              file=sys.stderr)
        exit(1)
    print('Please activate nix like described above, then re-run mach-nix.')
    exit(0)
