from os.path import abspath, dirname

from setuptools import setup, find_packages

pwd = dirname(abspath(__file__))
with open(pwd + '/mach_nix/VERSION') as f:
    version = f.read().strip()

setup(
    name='mach-nix',
    version=version,
    url='https://github.com/DavHau/mach-nix',
    author='David Hauer',
    author_email='hsngrmpf@gmail.com',
    description='Tool to create highly reproducible python environments',
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "mach-nix = mach_nix:main"
        ],
    },
    package_data={'': ['nix/*', 'VERSION', 'provider_defaults.toml']},
    install_requires=[
        'distlib ~= 0.3.0',
        'packaging >= 19.0',
        'resolvelib == 0.3.0',
    ],
)