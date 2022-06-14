import pytest

from mach_nix.data import providers
from mach_nix.data.providers import WheelRelease
from mach_nix.versions import PyVer


@pytest.mark.parametrize("expected, py_ver, wheel_fn, system, platform", [
    # with multiple versions
    (False, '2.7.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl', "linux", "x86_64"),
    (False, '3.4.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl', "linux", "x86_64"),
    (True, '3.5.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl', "linux", "x86_64"),
    (True, '3.6.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl', "linux", "x86_64"),
    (True, '3.7.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl', "linux", "x86_64"),
    (False, '3.8.0', 'PyQt5-5.15.1-5.15.1-cp35.cp36.cp37-abi3-manylinux2014_x86_64.whl', "linux", "x86_64"),
    # manylinux_${GLIBCMAJOR}_${GLIBCMINOR}
    (True, '3.9.0', 'pymaid-1.0.0a1-cp39-cp39-manylinux_2_5_x86_64.whl', "linux", "x86_64"),
    # combination of manylinux GLIBC* and YEAR formats
    (True, '3.6.0', 'tokenizers-0.10.3-cp36-cp36m-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl', "linux", "x86_64"),
    # none-any wheels for py2 + py3
    (True, '2.7.0', 'requests-2.24.0-py2.py3-none-any.whl', "linux", "x86_64"),
    (True, '3.8.0', 'requests-2.24.0-py2.py3-none-any.whl', "linux", "x86_64"),
    (True, '3.10.4', 'requests-2.24.0-py2.py3-none-any.whl', "linux", "x86_64"),
    (False, '4.0.0', 'requests-2.24.0-py2.py3-none-any.whl', "linux", "x86_64"),
    # none-any wheels for py2
    (True, '2.0.0', 'requests-2.24.0-py2-none-any.whl', "linux", "x86_64"),
    (False, '3.0.0', 'requests-2.24.0-py2-none-any.whl', "linux", "x86_64"),

    # darwin
    (True, '2.0.0', 'requests-2.24.0-py2-none-any.whl', "darwin", "x86_64"),
    (True, '3.8.0', 'tensorflow-2.3.1-cp38-cp38-macosx_10_14_x86_64.whl', "darwin", "x86_64"),
    (False, '3.8.0', 'tensorflow-2.3.1-cp35-cp35m-macosx_10_6_x86_64.whl', "darwin", "x86_64"),
    (False, '3.5.0', 'tensorflow-2.3.1-cp35-cp35m-macosx_10_6_intel.whl', "darwin", "x86_64"),  # intel not supported
])
def test_select_wheel_for_py_ver(expected, py_ver, wheel_fn, system, platform):
    prov = providers.WheelDependencyProvider('', py_ver=PyVer(py_ver), system=system, platform=platform)
    w = WheelRelease(*([""] * 3), wheel_fn, *([""] * 3))
    assert prov._wheel_type_ok(w) == expected
