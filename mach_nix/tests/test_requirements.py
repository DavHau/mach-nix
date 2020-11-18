import pytest

from mach_nix.requirements import parse_reqs_line


@pytest.mark.parametrize("exp_build, exp_line, line", [
    (None, 'requests==2.24.0', 'requests 2.24.0'),
    (None, 'requests == 2.24.0', 'requests == 2.24.0'),
    (None, 'requests==2.24.0', 'requests 2.24.0'),
    (None, 'requests==2.24.0', 'requests 2.24.0 '),
    (None, 'requests==2.24.0', ' requests 2.24.0 '),
    (None, 'pdfminer.six == 20200726', 'pdfminer.six == 20200726'),

    # multiple specs
    ("mpi_mpich_*", 'hdf5>=1.10.5,<1.10.6.0a0', 'hdf5 >=1.10.5,<1.10.6.0a0 mpi_mpich_*'),

    # asterisk
    ('openblas', 'blas==1.*', 'blas 1.* openblas'),
    ('openblas', 'blas==*', 'blas * openblas'),
    ('openblas', 'blas==1.1', 'blas 1.1 openblas'),
    ('build123*', 'requests>=2.24.0', 'requests >=2.24.0 build123*'),
    ('build123*', 'requests==2.24.*', 'requests ==2.24.* build123*'),
    ('build123*', 'requests==2.24.*', 'requests 2.24.* build123*'),
    ('build123*', 'requests==2.24.0', 'requests 2.24.0 build123*'),
    (None, 'requests==2.24.0', 'requests 2.24.0 *'),

    # stripping
    ('build123*', 'requests==2.24.0', ' requests 2.24.0 build123*'),
    ('build123*', 'requests==2.24.0', 'requests 2.24.0 build123* '),
    ('build123*', 'requests==2.24.0', ' requests 2.24.0 build123* '),

    # spacing
    (None, 'python>=3.5', 'python>= 3.5'),
    (None, 'python>=3.5', 'python >=3.5'),

    # test 3 parts non-conda
    (None, 'python >=2.6, !=3.0.*', 'python >=2.6, !=3.0.*'),

    # ignoring builds
    (None, 'requests==2.24.0', ' requests 2.24.0 py37_2'),
    (None, 'requests==2.24.0', ' requests 2.24.0 0'),
    (None, 'requests==2.24.0', ' requests 2.24.0 *'),
    (None, 'ca-certificates>=2020.10.14', 'ca-certificates >=2020.10.14 0'),
    ('py35hd5e75dd_0', 'requests==2.24.0', ' requests 2.24.0 py35hd5e75dd_0'),

])
def test_parse_requirements(exp_build, exp_line, line):
    new_line, build = parse_reqs_line(line)
    assert (build, new_line) == (exp_build, exp_line)
