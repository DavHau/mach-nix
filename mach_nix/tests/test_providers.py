import pytest

from mach_nix.data import providers
from mach_nix.data.providers import WheelRelease
from mach_nix.versions import PyVer


@pytest.mark.parametrize("expected, py_ver, wheel_fn", [
    # with multiple versions
    (False, '2.7.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl'),
    (False, '3.4.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl'),
    (True, '3.5.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl'),
    (True, '3.6.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl'),
    (True, '3.7.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl'),
    (False, '3.8.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl'),
    # none-any wheels for py2 + py3
    (True, '2.7.0', 'requests-2.24.0-py2.py3-none-any.whl'),
    (True, '3.8.0', 'requests-2.24.0-py2.py3-none-any.whl'),
    (False, '4.0.0', 'requests-2.24.0-py2.py3-none-any.whl'),
    # none-any wheels for py2
    (True, '2.0.0', 'requests-2.24.0-py2-none-any.whl'),
    (False, '3.0.0', 'requests-2.24.0-py2-none-any.whl'),
])
def test_select_wheel_for_py_ver(expected, py_ver, wheel_fn):
    prov = providers.WheelDependencyProvider('', py_ver=PyVer(py_ver), system="linux", platform="x86_64")
    w = WheelRelease(*([""] * 3), wheel_fn, *([""] * 3))
    assert prov._wheel_type_ok(w) == expected
