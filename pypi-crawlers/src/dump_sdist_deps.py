import sys
from dataclasses import asdict, dataclass
from typing import Set, Dict

from bucket_dict import LazyBucketDict
from db import Package as P


@dataclass
class PKG:
    install_requires: str
    setup_requires: str
    extras_require: str
    tests_require: str
    python_requires: str


def flatten_req_list(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        if len(obj) == 0:
            return
        elif len(obj) == 1:
            for s in flatten_req_list(obj[0]):
                yield s
        else:
            for elem in obj:
                for s in flatten_req_list(elem):
                    yield s
    else:
        raise Exception('Is not list or str')


flatten_keys = (
    'setup_requires',
    'install_requires',
    'tests_require',
    'python_requires',
)


def pkg_to_dict(pkg):
    pkg_dict = asdict(PKG(
        install_requires=pkg.install_requires,
        setup_requires=pkg.setup_requires,
        extras_require=pkg.extras_require,
        tests_require=pkg.tests_require,
        python_requires=pkg.python_requires
    ))
    new_release = {}
    for key, val in pkg_dict.items():
        if not val:
            continue
        if key == 'extras_require':
            for extra_key, extra_reqs in val.items():
                val[extra_key] = list(flatten_req_list(extra_reqs))
        if key not in flatten_keys:
            new_release[key] = val
            continue
        val = list(flatten_req_list(val))
        if isinstance(val, str):
            val = [val]
        if not all(isinstance(elem, str) for elem in val):
            print(val)
            raise Exception('Requirements must be list of strings')
        new_release[key] = val
    return new_release


def insert(py_ver, name, ver, release, target):
    ver = ver.strip()
    # create structure
    if name not in target:
        target[name] = {}
    if ver not in target[name]:
        target[name][ver] = {}
    # if exact same pkg data already exists for another version,
    # just refer to other version to prevent duplicates
    for py, existing_pkg in target[name][ver].items():
        if release == existing_pkg:
            target[name][ver][py_ver] = py
            return
    target[name][ver][py_ver] = release


def get_names_per_bucket() -> Dict[str, Set[str]]:
    result = {}
    hexdigits = "0123456789abcdef"
    for a in hexdigits:
        for b in hexdigits:
            result[a + b] = set()
    keys = [p.name for p in P.select(P.name).distinct()]
    for key in keys:
        result[LazyBucketDict.bucket(key)].add(key)
    return result


def compress_dict(d, sort=True):
    if sort:
        items = sorted(d.items(), key=lambda x: x[0])
    else:
        items = d.items()
    keep = {}
    for k, v in items:
        for keep_key, keep_val in keep.items():
            if v == keep_val:
                d[k] = keep_key
                break
        if not isinstance(d[k], str):
            keep[k] = v


def compress(pkgs_dict: LazyBucketDict):
    for name, vers in pkgs_dict.items():
        for ver, pyvers in vers.items():
            compress_dict(pyvers)
        compress_dict(vers)


def main():
    dump_dir = sys.argv[1]
    for bucket_key, key_set in get_names_per_bucket().items():
        pkgs_dict = LazyBucketDict(f"{dump_dir}", restrict_to_bucket=bucket_key)
        pkgs = P.select(
            P.id,
            P.name,
            P.version,
            P.py_ver,
            P.install_requires,
            P.setup_requires,
            P.extras_require,
            P.tests_require,
            P.python_requires,
        ).where(P.error.is_null(), P.name.in_(key_set))
        print(f'dumping bucket {bucket_key}')
        for pkg in sorted(pkgs, key=lambda pkg: (pkg.name, pkg.version, pkg.py_ver)):
            py_ver = ''.join(filter(lambda c: c.isdigit(), pkg.py_ver))
            insert(py_ver, pkg.name, pkg.version, pkg_to_dict(pkg), pkgs_dict)
        compress(pkgs_dict)
        pkgs_dict.save()


if __name__ == "__main__":
    main()
