import json
import os
import subprocess as sp
import traceback
from dataclasses import dataclass, field
from random import shuffle
from tempfile import TemporaryDirectory
from time import sleep, time
from typing import Union, List, ContextManager

import utils
from bucket_dict import LazyBucketDict
from db import db, Package, init_db


@dataclass
class PackageJob:
    bucket: str
    name: str
    version: str
    url: Union[None, str]
    sha256: Union[None, str]
    idx: int
    timeout: int = field(default=60)


@dataclass
class JobResult:
    name: str
    version: str
    error: Union[None, str]
    install_requires: Union[None, str, list, dict]
    setup_requires: Union[None, str, list, dict]
    extras_require: Union[None, str, list, dict]
    python_requires: Union[None, str, list, dict]


def extractor_cmd(pkg_name, pkg_ver, out='./result', url=None, sha256=None, substitutes=True, store=None) -> List[str]:
    extractor_dir = os.environ.get("extractor_dir")
    if not extractor_dir:
        raise Exception("Set env variable 'extractor_dir'")
    base_args = [
        "--arg", "pkg", f'"{pkg_name}"',
        "--arg", "version", f'"{pkg_ver}"',
        "-o", out
    ]
    if store:
        base_args += ["--store", f"{store}"]
    if url and sha256:
        cmd = [
            "nix-build", f"{extractor_dir}/fast-extractor.nix",
            "--arg", "url", f'"{url}"',
            "--arg", "sha256", f'"{sha256}"'
        ] + base_args
    else:
        cmd = [
            "nix-build", f"{extractor_dir}/extractor.nix",
        ] + base_args
        print('using slow builder')
    if not substitutes:
        cmd += ["--option", "build-use-substitutes", "false"]
    return cmd


def format_log(log: str):
    """
    Postgres doesn't support indexing large text files.
    Therefore we limit line length and count
    """
    lines = log.splitlines(keepends=True)
    lines = map(lambda line: f"{line[:400]}\n" if len(line) > 400 else line, lines)
    remove_lines_marker = (
        '/homeless-shelter/.cache/pip/http',
        '/homeless-shelter/.cache/pip',
        'DEPRECATION: Python 2.7'
    )
    filtered = filter(lambda l: not any(marker in l for marker in remove_lines_marker), lines)
    return ''.join(list(filtered)[:90])


def extract_requirements(job: PackageJob):
    py_versions = ('python27', 'python38', 'python39', 'python310', 'python311')
    try:
        print(f"Bucket {job.bucket} - Job {job.idx} - {job.name}:{job.version}")
        store = os.environ.get('STORE', None)
        with TemporaryDirectory() as tempdir:
            out_dir = f"{tempdir}/json"
            cmd = extractor_cmd(job.name, job.version, out_dir, job.url, job.sha256,
                                store=store)
            #print(' '.join(cmd).replace(' "', ' \'"').replace('" ', '"\' '))
            try:
                sp.run(cmd, capture_output=True, timeout=job.timeout, check=True)
            except (sp.CalledProcessError, sp.TimeoutExpired) as e:
                print(f"problem with {job.name}:{job.version}")
                print(e.stderr.decode())
                formatted = format_log(e.stderr.decode())
                return [dict(
                    name=job.name,
                    version=job.version,
                    py_ver=f"{py_ver}",
                    error=formatted,
                ) for py_ver in py_versions]
            results = []
            for py_ver in py_versions:
                data = None
                try:
                    path = os.readlink(f"{out_dir}")
                    if store:
                        path = path.replace('/nix/store', f"{store}/nix/store")
                    with open(f"{path}/{py_ver}.json") as f:
                        content = f.read().strip()
                        if content != '':
                            data = json.loads(content)
                except FileNotFoundError:
                    pass
                if data is None:
                    with open(f"{path}/{py_ver}.log") as f:
                        error = format_log(f.read())
                    print(error)
                    results.append(dict(
                        name=job.name,
                        version=job.version,
                        py_ver=f"{py_ver}",
                        error=error,
                    ))
                else:
                    for k in ('name', 'version'):
                        if k in data:
                            del data[k]
                    results.append(dict(
                        name=job.name,
                        version=job.version,
                        py_ver=py_ver,
                        **data
                    ))
            return results
    except Exception as e:
        traceback.print_exc()
        return e


def get_jobs(pypi_fetcher_dir, bucket, processed, amount=1000):
    pypi_dict = LazyBucketDict(f"{pypi_fetcher_dir}/pypi", restrict_to_bucket=bucket)
    jobs = []
    names = list(pypi_dict.by_bucket(bucket).keys())
    total_nr = 0
    for pkg_name in names:
        for ver, release_types in pypi_dict[pkg_name].items():
            if 'sdist' not in release_types:
                continue
            if (pkg_name, ver) in processed:
                continue
            total_nr += 1
            release = release_types['sdist']
            if len(jobs) <= amount:
                jobs.append(PackageJob(
                    bucket,
                    pkg_name,
                    ver,
                    f"https://files.pythonhosted.org/packages/source/{pkg_name[0]}/{pkg_name}/{release[1]}",
                    release[0],
                    0,
                ))
    shuffle(jobs)
    for i, job in enumerate(jobs):
        job.idx = i
    print(f"Bucket {bucket}: Planning execution of {len(jobs)} jobs out of {total_nr} total jobs for this bucket")
    return jobs


def get_processed():
    with open('/tmp/jobs', 'r') as f:
        return {tuple(t) for t in json.load(f)}


def build_base(store=None):
    # make sure base stuff gets back into cache after cleanup:
    cmd = extractor_cmd("requests", "2.22.0", out='/tmp/dummy', url='https://files.pythonhosted.org/packages/01/62/ddcf76d1d19885e8579acb1b1df26a852b03472c0e46d2b959a714c90608/requests-2.22.0.tar.gz',
                        sha256='11e007a8a2aa0323f5a921e9e6a2d7e4e67d9877e85773fba9ba6419025cbeb4', store=store)
    sp.check_call(cmd, timeout=1000)


def cleanup():
    sp.check_call('rm -rf ./dummy', shell=True)
    cmd = "nix-collect-garbage"
    store = os.environ.get('almighty_store', None)
    if store:
        cmd += f" --store {store}"
    sp.check_call(cmd, shell=True)


def ensure_pypi_fetcher(dir):
    if not os.path.isdir(dir):
        cmd = f'git clone git@github.com:DavHau/nix-pypi-fetcher-2.git {dir}'
        sp.check_call(cmd, shell=True)
    sp.check_call("git checkout master && git pull", shell=True, cwd=dir)


class Measure(ContextManager):
    def __init__(self, name):
        self.name = name
    def __enter__(self):
        self.enter_time = time()
        print(f'beginning "{self.name}"')
    def __exit__(self, exc_type, exc_val, exc_tb):
        dur = round(time() - self.enter_time, 1)
        print(f'"{self.name}" took {dur}s')


def main():
    workers = int(os.environ.get('WORKERS', "1"))
    pypi_fetcher_dir = os.environ.get('pypi_fetcher', '/tmp/pypi_fetcher')
    ensure_pypi_fetcher(pypi_fetcher_dir)
    init_db()
    build_base(store=os.environ.get('STORE', None))
    P = Package
    with Measure('Get processed pkgs from DB'):
        processed = set((p.name, p.version) for p in P.select(P.name, P.version).distinct())
        print(f"DB contains {len(processed)} pkgs at this time")
    for bucket in LazyBucketDict.bucket_keys():
        with Measure("getting jobs"):
            jobs = get_jobs(pypi_fetcher_dir, bucket, processed, amount=1000)
            if not jobs:
                continue
        with Measure('batch'):
            if workers > 1:
                pool_results = utils.parallel(extract_requirements, (jobs,), workers=workers, use_processes=False)
            else:
                pool_results = [extract_requirements(args) for args in jobs]
        results = []
        for i, res in enumerate(pool_results):
            if isinstance(res, Exception):
                print(f"Problem with {jobs[i].name}:{jobs[i].version}")
                if isinstance(res, sp.CalledProcessError):
                    print(res.stderr)
                traceback.print_exception(res, res, res.__traceback__)
            else:
                for r in res:
                    results.append(r)
        sleep(1)
        with db.atomic():
            with Measure('bulk insert'):
                Package.bulk_create([Package(**r) for r in results])
        if os.environ.get('CLEANUP', None):
            cleanup()


if __name__ == "__main__":
    main()
