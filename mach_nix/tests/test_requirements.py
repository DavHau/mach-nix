import pytest

from mach_nix.requirements import parse_reqs_line


@pytest.mark.parametrize("exp_build, exp_line, line", [
    # with multiple versions
    (None, 'requests==2.24.0', 'requests 2.24.0'),
    (None, 'requests == 2.24.0', 'requests == 2.24.0'),
    (None, 'requests==2.24.0', 'requests 2.24.0'),
    (None, 'requests==2.24.0', 'requests 2.24.0 '),
    (None, 'requests==2.24.0', ' requests 2.24.0 '),
    (None, 'pdfminer.six == 20200726', 'pdfminer.six == 20200726'),
    ('openblas', 'blas==1.*', 'blas 1.* openblas'),
    ('openblas', 'blas==*', 'blas * openblas'),
    ('openblas', 'blas==1.1', 'blas 1.1 openblas'),
    ('build123*', 'requests>=2.24.0', 'requests >=2.24.0 build123*'),
    ('build123*', 'requests>=2.24.0', 'requests >=2.24.0 build123*'),
    ('build123*', 'requests==2.24.*', 'requests ==2.24.* build123*'),
    ('build123*', 'requests==2.24.*', 'requests 2.24.* build123*'),
    ('build123*', 'requests==2.24.0', 'requests 2.24.0 build123*'),
    ('build123*', 'requests==2.24.0', ' requests 2.24.0 build123*'),
    ('build123*', 'requests==2.24.0', 'requests 2.24.0 build123* '),
    ('build123*', 'requests==2.24.0', ' requests 2.24.0 build123* '),

])
def test_parss_requirements(exp_build, exp_line, line):
    new_line, build = parse_reqs_line(line)
    assert (build, new_line) == (exp_build, exp_line)
