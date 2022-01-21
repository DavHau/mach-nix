import json
import sys

from importlib_metadata import Distribution
from pep517.wrappers import Pep517HookCaller

_, out, source, python, backend, backend_path = sys.argv

hooks = Pep517HookCaller(
    source, build_backend=backend, python_executable=python, backend_path=backend_path
)
dist = Distribution.at(hooks.prepare_metadata_for_build_wheel("."))

with open(out, "x") as f:
    json.dump(dist.metadata.json, f)