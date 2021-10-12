import sys
import traceback

import packaging.version
from packaging.version import parse as parse_ver, Version

__all__ = ['parse_ver', 'Version', 'PyVer']


class PyVer:
    def __init__(self, vstr):
        self.version = packaging.version.Version(vstr)

    def nix(self):
        res = 'python'
        res += str(self.version.release[0])
        if len(self.version.release) >= 2:
            res += str(self.version.release[1])
        return res

    def digits(self):
        return ''.join(map(str, self.version.release[:2]))

    def python_version(self):
        return f"{self.version.release[0]}.{self.version.release[1]}"

    def python_full_version(self):
        try:
            return f"{self.version.release[0]}.{self.version.release[1]}.{self.version.release[2]}"
        except IndexError:
            traceback.print_exc()
            print("Error: please specify full python version including bugfix version (like 3.7.5)", file=sys.stderr)
            exit(1)
