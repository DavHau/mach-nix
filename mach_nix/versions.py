import sys
import traceback

import packaging.version
from packaging.version import parse as parse_ver, Version
from conda.models.version import VersionOrder

__all__ = ['parse_ver', 'Version', 'PyVer']

class PyVer(VersionOrder):
    def __init__(self, vstr):
        self.pypa_ver = packaging.version.Version(vstr)
        super(PyVer, self).__init__(vstr)

    def nix(self):
        res = 'python'
        res += str(self.pypa_ver.release[0])
        if len(self.pypa_ver.release) >= 2:
            res += str(self.pypa_ver.release[1])
        return res

    def digits(self):
        return ''.join(filter(lambda c: c.isdigit(), str(self.pypa_ver)))[:2]

    def python_version(self):
        return f"{self.pypa_ver.release[0]}.{self.pypa_ver.release[1]}"

    def python_full_version(self):
        try:
            return f"{self.pypa_ver.release[0]}.{self.pypa_ver.release[1]}.{self.pypa_ver.release[2]}"
        except IndexError:
            traceback.print_exc()
            print("Error: please specify full python version including bugfix version (like 3.7.5)", file=sys.stderr)
            exit(1)
