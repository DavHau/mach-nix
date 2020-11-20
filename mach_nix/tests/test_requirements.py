import pytest

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
    , ("pywin32 > 1.0 : sys.platform == 'win32'", ('pywin32', (), ((('>', '1.0'),),), None, "sys.platform == 'win32'"))
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
])
def test_parse_requirements(input, exp_output):
    assert parse_reqs_line(input) == exp_output
