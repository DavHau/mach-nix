import json
from os import environ

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
import pytest

from mach_nix.data.bucket_dict import LazyBucketDict
from mach_nix.requirements import parse_reqs_line


@pytest.mark.parametrize("input, exp_output", [

    ('requests', ('requests', (), None, None, None))
    , ('requests[socks] ==2.24.0', ('requests', ('socks',), (SpecifierSet('==2.24.0'),), None, None))
    , ('requests[socks,test] 2.24.0', ('requests', ('socks', 'test'), (SpecifierSet('==2.24.0'),), None, None))
    , ('python >=2.7,<2.8.0a0', ('python', (), (SpecifierSet('>=2.7,<2.8.0a0'),), None, None))
    , ('requests == 2.24.0', ('requests', (), (SpecifierSet('==2.24.0'),), None, None))
    , ('pdfminer.six == 20200726', ('pdfminer.six', (), (SpecifierSet('==20200726'),), None, None))
    , ('python>= 3.5', ('python', (), (SpecifierSet('>=3.5'),), None, None))
    , ('python >=3.5', ('python', (), (SpecifierSet('>=3.5'),), None, None))
    , ('python >=2.6, !=3.0.*', ('python', (), (SpecifierSet('>=2.6,!=3.0.*'),), None, None))
    , ("unittest2 >=2.0,<3.0 ; python_version == '2.4' or python_version == '2.5'",
       ('unittest2', (), (SpecifierSet('>=2.0,<3.0'),), None, "python_version == '2.4' or python_version == '2.5'"))
    , ("pywin32 > 1.0 ; sys.platform == 'win32'", ('pywin32', (), (SpecifierSet('>1.0'),), None, "sys.platform == 'win32'"))
    , ("certifi (==2016.9.26) ; extra == 'certs'",
       ('certifi', ('certs',), (SpecifierSet('==2016.9.26'),), None, "extra == 'certs'"))
    , ("sphinx ; extra == 'docs'", ('sphinx', ('docs',), None, None, "extra == 'docs'"))
    , ('requests 2.24.0', ('requests', (), (SpecifierSet('==2.24.0'),), None, None))
    , ('requests 2.24.0', ('requests', (), (SpecifierSet('==2.24.0'),), None, None))
    , ('requests 2.24.0', ('requests', (), (SpecifierSet('==2.24.0'),), None, None))
    , ('requests 2.24.0', ('requests', (), (SpecifierSet('==2.24.0'),), None, None))
    , ('hdf5 >=1.10.5,<1.10.6.0a0 mpi_mpich_*',
       ('hdf5', (), (SpecifierSet('>=1.10.5,<1.10.6.0a0'),), 'mpi_mpich_*', None))
    , ('blas 1.* openblas', ('blas', (), (SpecifierSet('==1.*'),), 'openblas', None))
    , ('blas 1.1 openblas', ('blas', (), (SpecifierSet('==1.1'),), 'openblas', None))
    , ('requests >=2.24.0 build123*', ('requests', (), (SpecifierSet('>=2.24.0'),), 'build123*', None))
    , ('requests ==2.24.* build123*', ('requests', (), (SpecifierSet('==2.24.*'),), 'build123*', None))
    , ('requests 2.24.* build123*', ('requests', (), (SpecifierSet('==2.24.*'),), 'build123*', None))
    , ('requests 2.24.0 build123*', ('requests', (), (SpecifierSet('==2.24.0'),), 'build123*', None))
    , ('requests 2.24.0 *bla', ('requests', (), (SpecifierSet('==2.24.0'),), '*bla', None))
    , ('requests 2.24.0 *', ('requests', (), (SpecifierSet('==2.24.0'),), '*', None))
    , ('requests 2.24.0 build123*', ('requests', (), (SpecifierSet('==2.24.0'),), 'build123*', None))
    , ('requests 2.24.0 build123*', ('requests', (), (SpecifierSet('==2.24.0'),), 'build123*', None))
    , ('requests 2.24.0 build123*', ('requests', (), (SpecifierSet('==2.24.0'),), 'build123*', None))
    , ('ruamel.yaml >=0.12.4,<0.16|0.16.5.*',
       ('ruamel.yaml', (), (SpecifierSet('>=0.12.4,<0.16'), SpecifierSet('==0.16.5.*')), None, None))
    , ('openjdk =8|11', ('openjdk', (), (SpecifierSet('==8'), SpecifierSet('==11')), None, None))
    , ('python 3.6.9 ab_73_pypy', ('python', (), (SpecifierSet('==3.6.9'),), 'ab_73_pypy', None))
    , ('gitpython >=3.0.8,3.0.*', ('gitpython', (), (SpecifierSet('>=3.0.8,==3.0.*'),), None, None))
    , ("zest.releaser[recommended] ; extra == 'maintainer'",
       ('zest.releaser', ('recommended', 'maintainer'), None, None, "extra == 'maintainer'"))
    , ('pytz (>dev)', ('pytz', (), (), None, None))
    , ('libcurl 7.71.1 h20c2e04_1', ('libcurl', (), (SpecifierSet('==7.71.1'),), 'h20c2e04_1', None))
    , ('ixmp ==0.1.3 1', ('ixmp', (), (SpecifierSet('==0.1.3',),), '1', None))
])
def test_parse_requirements(input, exp_output):
    assert parse_reqs_line(input) == exp_output

# Pypi packages contain a lot of invalid requirement syntax.
# All lines that can't be parsed by packaging are ignored.
# Additionally, some syntax that we don't currently support
# are ignored.
# All other lines must be parsed without errors.
def parse_or_ignore_line(line):
    lineStripped = line.strip().replace("'", "").replace('"', '')
    if not len(lineStripped):
        return
    if line.startswith("#"):
        return
    # We don't currently support requirements with these.
    unsupported = (
        "@",
        "===",
    )
    if any((x in lineStripped for x in unsupported)):
        return
    # We turn the DeprecationWarning raised by
    # packaging.specifier.LegacySpecifier into an error in
    # test_parse_all_pypi_reqs below, so this will raise in
    # that case.
    try:
        Requirement(line)
    except Exception:
        return False
    parse_reqs_line(line)


def parse_or_ignore_line_conda(line):
    # lineStripped = line.strip().replace("'", "").replace('"', '')
    lineStripped = line
    # if not len(lineStripped):
    #     return
    # if line.startswith("#"):
    #     return
    if any(lineStripped.startswith(x) for x in [

    ]):
        return
    if any(lineStripped.endswith(x) for x in [

    ]):
        return
    if any((x in lineStripped for x in [
        'blas *.* mkl'
    ])):
        return
    parse_reqs_line(line)


# Constructing a packaging.specifiers.LegacySpecifier
# issues a warning containing "LegacyVersion". We
# turn it into an error here, so we can treat it as
# unparseable.
@pytest.mark.filterwarnings("error:.*LegacyVersion.*:DeprecationWarning")
@pytest.mark.parametrize("bucket", LazyBucketDict.bucket_keys())
def test_parse_all_pypi_reqs(bucket):
    data_dir = environ.get("PYPI_DATA", default=None)
    data = LazyBucketDict(f"{data_dir}/sdist")
    for pname, vers in data.by_bucket(bucket).items():
        for ver, pyvers in vers.items():
            if isinstance(pyvers, str):
                continue
            for pyver, release in pyvers.items():
                if isinstance(release, str):
                    continue
                for key in ("setup_requires", "install_requires"):
                    if key in release:
                        for line in release[key]:
                            parse_or_ignore_line(line)
                if "extras_require" in release:
                    for extra, lines in release["extras_require"].items():
                        for line in lines:
                            parse_or_ignore_line(line)


def conda_channel_files():
    conda_data = environ.get("CONDA_DATA", None)
    if not conda_data:
        return []
    with open(conda_data) as f:
        data = json.load(f)
    for channel, files in data.items():
        for file in files:
            yield file


@pytest.mark.skipif(conda_channel_files() == [], reason="no CONDA_DATA provided")
@pytest.mark.parametrize("file", conda_channel_files())
def test_parse_all_conda_reqs(file):
    with open(file) as f:
        cdata = json.load(f)
    for pname, pdata in cdata['packages'].items():
        for line in pdata['depends']:
            parse_or_ignore_line_conda(line)
