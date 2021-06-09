import json
from os import environ

import pytest

from mach_nix.data.bucket_dict import LazyBucketDict
from mach_nix.requirements import parse_reqs_line


@pytest.mark.parametrize("input, exp_output", [

    ('requests', ('requests', (), None, None, None))
    , ('requests[socks] ==2.24.0', ('requests', ('socks',), ((('==', '2.24.0'),),), None, None))
    , ('requests[socks,test] 2.24.0', ('requests', ('socks', 'test'), ((('==', '2.24.0'),),), None, None))
    , ('python >=2.7,<2.8.0a0', ('python', (), ((('>=', '2.7'), ('<', '2.8.0a0')),), None, None))
    , ('requests == 2.24.0', ('requests', (), ((('==', '2.24.0'),),), None, None))
    , ('pdfminer.six == 20200726', ('pdfminer.six', (), ((('==', '20200726'),),), None, None))
    , ('python>= 3.5', ('python', (), ((('>=', '3.5'),),), None, None))
    , ('python >=3.5', ('python', (), ((('>=', '3.5'),),), None, None))
    , ('python >=2.6, !=3.0.*', ('python', (), ((('>=', '2.6'), ('!=', '3.0.*')),), None, None))
    , ("unittest2 >=2.0,<3.0 ; python_version == '2.4' or python_version == '2.5'",
       ('unittest2', (), ((('>=', '2.0'), ('<', '3.0')),), None, "python_version == '2.4' or python_version == '2.5'"))
    , ("pywin32 > 1.0 ; sys.platform == 'win32'", ('pywin32', (), ((('>', '1.0'),),), None, "sys.platform == 'win32'"))
    , ("certifi (==2016.9.26) ; extra == 'certs'",
       ('certifi', ('certs',), ((('==', '2016.9.26'),),), None, "extra == 'certs'"))
    , ("sphinx ; extra == 'docs'", ('sphinx', ('docs',), None, None, "extra == 'docs'"))
    , ('requests 2.24.0', ('requests', (), ((('==', '2.24.0'),),), None, None))
    , ('requests 2.24.0', ('requests', (), ((('==', '2.24.0'),),), None, None))
    , ('requests 2.24.0', ('requests', (), ((('==', '2.24.0'),),), None, None))
    , ('requests 2.24.0', ('requests', (), ((('==', '2.24.0'),),), None, None))
    , ('hdf5 >=1.10.5,<1.10.6.0a0 mpi_mpich_*',
       ('hdf5', (), ((('>=', '1.10.5'), ('<', '1.10.6.0a0')),), 'mpi_mpich_*', None))
    , ('blas 1.* openblas', ('blas', (), ((('==', '1.*'),),), 'openblas', None))
    , ('blas * openblas', ('blas', (), ((('==', '*'),),), 'openblas', None))
    , ('blas 1.1 openblas', ('blas', (), ((('==', '1.1'),),), 'openblas', None))
    , ('requests >=2.24.0 build123*', ('requests', (), ((('>=', '2.24.0'),),), 'build123*', None))
    , ('requests ==2.24.* build123*', ('requests', (), ((('==', '2.24.*'),),), 'build123*', None))
    , ('requests 2.24.* build123*', ('requests', (), ((('==', '2.24.*'),),), 'build123*', None))
    , ('requests 2.24.0 build123*', ('requests', (), ((('==', '2.24.0'),),), 'build123*', None))
    , ('requests 2.24.0 *bla', ('requests', (), ((('==', '2.24.0'),),), '*bla', None))
    , ('requests 2.24.0 *', ('requests', (), ((('==', '2.24.0'),),), '*', None))
    , ('requests * *bla', ('requests', (), ((('==', '*'),),), '*bla', None))
    , ('requests * *', ('requests', (), ((('==', '*'),),), '*', None))
    , ('requests 2.24.0 build123*', ('requests', (), ((('==', '2.24.0'),),), 'build123*', None))
    , ('requests 2.24.0 build123*', ('requests', (), ((('==', '2.24.0'),),), 'build123*', None))
    , ('requests 2.24.0 build123*', ('requests', (), ((('==', '2.24.0'),),), 'build123*', None))
    , ('ruamel.yaml >=0.12.4,<0.16|0.16.5.*',
       ('ruamel.yaml', (), ((('>=', '0.12.4'), ('<', '0.16')), (('==', '0.16.5.*'),)), None, None))
    , ('openjdk =8|11', ('openjdk', (), ((('==', '8'),), (('==', '11'),)), None, None))
    , ('python 3.6.9 ab_73_pypy', ('python', (), ((('==', '3.6.9'),),), 'ab_73_pypy', None))
    , ('gitpython >=3.0.8,3.0.*', ('gitpython', (), ((('>=', '3.0.8'), ('==', '3.0.*')),), None, None))
    , ("zest.releaser[recommended] ; extra == 'maintainer'",
       ('zest.releaser', ('recommended', 'maintainer'), None, None, "extra == 'maintainer'"))
    , ('pytz (>dev)', ('pytz', (), ((('>', 'dev'),),), None, None))
    , ('libcurl 7.71.1 h20c2e04_1', ('libcurl', (), ((('==', '7.71.1'),),), 'h20c2e04_1', None))
])
def test_parse_requirements(input, exp_output):
    assert parse_reqs_line(input) == exp_output


# Pypi packages contain a lot of invalid requirement syntax.
# All corrupted patterns are listed here.
# All other lines must be parsed without errors.
def parse_or_ignore_line(line):
    lineStripped = line.strip().replace("'", "").replace('"', '')
    if not len(lineStripped):
        return
    if line.startswith("#"):
        return
    if any(lineStripped.startswith(x) for x in [
        '3>',
    ]):
        return
    if any(lineStripped.endswith(x) for x in [
        # theoretically some of these are valid legacy versions,
        # but no sane package uses those anyways
        '==trunk',
        '=master',
        '==edge',
        '==Windows',
        '==spdy',
        '>=pyparsing',
        '>=pandas',
        '>',
        '=',
    ]):
        return
    exclude = (
        "\n",
        "@",
        '&',
        'numpy>=1.14.4+mkl',
        '!',
        '+',
        '>~',
        '],',
        '>>',
        '<.',
        '>.',
        '>>=',
        '>-=',
        '>==',
        '>i=',
        '>=>',
        '>=^',
        '===',
        '=.',
        '>=X.Y',
        "pytest-remotedata>=0.3.1'",
        'asv_utils>=dev-20110615-01',
        'scipy>=O.19',  # this is a capital 'o' not a '0'
        'boto3>=boto3-1.17.57',
        'scikit-learn>=0.24.1mdf_connect_client>=0.3.8',
        '=version=',
        'rasterio>=1.0a10[s3]',
        'docker>=3.5.0jupyter_client>=5.2.0',
        'pytest==cov-2.5.1',
        'requests>',
        'pyhive>=0.3.0[Hive]',
        'pyhive>=0.3.0[Presto]',
        'python>dateutil==2.7.5',
        'Flask>PyMongo==2.3.0',
        'Flask>RESTful==0.3.7',
        'connexion==2.7.0connexion[openapi-ui]==0.0.6flask==1.1.1Flask-SQLAlchemy==2.4.4'
            'flask-marshmallowmarshmallowmarshmallow-sqlalchemyWerkzeug',
        'orthauth>=0.0.13[yaml]',
        'tensorflow>=2.4.0ray[tune]',
        'Twisted>=17[tls]',
        'numpy >= numpy==1.17.2',
        'pandas==pandas-0.24.2',
        'dapr-dev>=dapr-dev-0.6.0a0.dev67',
        'Twisted>=17[tls]',
        'aiida-core<=0.12.3[atomic_tools]',
        'certifi>=certifi-2018.8.24',
        'Unidecode==1.1.1]',
        'django-nose==commit.7fd013209',
        'testflows.core>=testflows.core-1.6.200713.1230254',
        'gym>=0.9.1[all]',
        'aiida_core>=0.12.0[atomic_tools]',
        'dnspython<2requests[security]',
        'aiohttp>aiohttp>3.6.2',
        'sqlalchemy>=1.2.12[postgresql]',
        'bw2io>=RC3',
        'twisted>=twisted-13.2',
        'pyodbc==virtuoso-2.1.9-beta14',
        'cairocffi>=0.7[xcb]',
        'PySide2>=2.0.0~alpha0',
        'keyboard==0.13.3=pypi_0',
        'numpy>=numpy==1.17.2',
        'aiida-core>=1.0.0b1[atomic_tools]',
        'aiohttp>aiohttp>=3.6.2',
        'cairocffi>=0.9[xcb]',
        'numpy==1.18.1=pypi_0',
        'psutil==^5.7.0',
        'Twisted>=Twisted-13.2',
        'pandas==asa',
    )
    if any((x in lineStripped for x in exclude)):
        return
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
    with open(environ.get("CONDA_DATA", None)) as f:
        data = json.load(f)
    for channel, files in data.items():
        for file in files:
            yield file


@pytest.mark.parametrize("file", conda_channel_files())
def test_parse_all_conda_reqs(file):
    with open(file) as f:
        cdata = json.load(f)
    for pname, pdata in cdata['packages'].items():
        for line in pdata['depends']:
            parse_or_ignore_line_conda(line)

