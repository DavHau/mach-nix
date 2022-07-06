import json
import sys

from importlib_metadata import Distribution
from pep517.wrappers import Pep517HookCaller

_, out, source, python, backend, backend_path, command, *args = sys.argv

hooks = Pep517HookCaller(
    source, build_backend=backend, python_executable=python, backend_path=backend_path
)
if command == "build-requires":
    output = hooks.get_requires_for_build_wheel()
elif command == "metadata":
    dist = Distribution.at(hooks.prepare_metadata_for_build_wheel("."))
    (build_requires_path,) = args
    with open(build_requires_path) as f:
        build_requires = json.load(f)
    output = dist.metadata.json
    output["build-requires"] = build_requires

with open(out, "x") as f:
    json.dump(output, f)
