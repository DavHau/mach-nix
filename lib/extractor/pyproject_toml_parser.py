# requirements extractor for pyproject.toml  projects (Poetry, flint, pep621).
import os
import toml
import json


# Load the pyproject.toml file
with open("pyproject.toml", "r") as file:
    pyproject = toml.load(file)
    print("pyproject.toml loaded")
    import pprint

    pprint.pprint(pyproject)


def parse_to_setup_requirements(key, value):
    """We need to turn ^ requirements into >= and < requirements"""
    if "^" in value:
        major_version = int(value.split(".")[0].replace("^", ""))
        if major_version > 0:
            next_major_version = str(major_version + 1)
            return f'{key}>={value.replace("^", "")},<{next_major_version}.0.0'
        else:
            # when it's ^0.x, we need ^0.(x+10).0
            minor_version = int(value.split(".")[1].replace("^", ""))
            next_minor_version = str(minor_version + 1)
            return f'{key}>={value.replace("^", "")},<0.{next_minor_version}.0'

    else:
        return f"{key}{value}"


def parse_req_from_str(key_value):
    if "^" in key_value:
        pkg, version = key_value.split("^")
        return parse_to_setup_requirements(pkg, "^" + version)
    else:
        return key_value


def parse_poetry(pyproject):
    dependencies = {}
    dependencies["name"] = pyproject["tool"]["poetry"]["name"]
    dependencies["version"] = pyproject["tool"]["poetry"]["version"]
    dependencies["install_requires"] = []
    for key, value in pyproject["tool"]["poetry"]["dependencies"].items():
        if key == "python":
            dependencies["python_requires"] = value.replace("^", ">=")
        else:
            dependencies["install_requires"].append(
                parse_to_setup_requirements(key, value)
            )

    dependencies["extras_require"] = {}
    for key, value in pyproject["tool"]["poetry"]["dev-dependencies"].items():
        dependencies["extras_require"].setdefault("dev", []).append(f"{key}")
    return dependencies


def parse_flit(pyproject):
    dependencies = {}
    # Parse the dependencies into the desired format
    metadata = pyproject["tool"]["flit"]["metadata"]
    dependencies["name"] = metadata.get("module")
    dependencies["version"] = ""  # Flit doesn't have a version field in pyproject.toml
    if "requires-python" in metadata:
        dependencies["python_requires"] = metadata.get("requires-python", "")

    dependencies["install_requires"] = []

    if "requires" in metadata:
        for requirement in metadata["requires"]:
            dependencies["install_requires"].append(parse_req_from_str(requirement))

    dependencies["extras_require"] = {}
    if "dev-requires" in metadata:
        for key, value in metadata["dev-requires"].items():
            dependencies["extras_require"].setdefault("dev", []).append(
                parse_to_setup_requirements(key, value)
            )
    return dependencies


def parse_pep621(pyproject):
    # Parse the dependencies into the desired format
    project = pyproject["project"]
    dependencies = {
        "name": project.get("name"),
        "version": project.get("version"),
        "python_requires": project.get("requires-python", ""),
        "install_requires": [],
        "extras_require": {},
    }
    if "dependencies" in project:
        for key_value in project["dependencies"]:
            dependencies["install_requires"].append(parse_req_from_str(key_value))
    if "optional-dependencies" in project:
        for key, values in project["optional-dependencies"].items():
            dependencies["extras_require"][key] = []
            for pkg_version in values:
                dependencies["extras_require"][key].append(
                    parse_req_from_str(pkg_version)
                )
    return dependencies


if pyproject.get("project", None):
    print("detected pep 621 format project")
    dependencies = parse_pep621(pyproject)
elif pyproject.get("tool", {}).get("poetry", None):
    print("detected poetry format project")
    dependencies = parse_poetry(pyproject)
elif pyproject.get("tool", {}).get("flit", None):
    print("detected flit format project")
    dependencies = parse_flit(pyproject)
else:
    print(
        "No supported requirements specification in pyproject.toml. Currently only pep621, flit and poetry are supported."
        " Though of course this might just mean your package has no requirements."
    )
    dependencies = {}

if "build-system" in pyproject:
    dependencies["setup_requires"] = [
        parse_req_from_str(key_value)
        for key_value in pyproject["build-system"].get("requires", [])
    ]

out_file = os.environ.get("out_file", "python.json")
with open(out_file, "w") as file:
    print(f"storing dependencies in {out_file}")
    json.dump(dependencies, file, indent=2)
