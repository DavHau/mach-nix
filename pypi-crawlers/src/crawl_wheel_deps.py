import json
import os
import sys
import traceback
import zipfile
from dataclasses import dataclass
from os.path import isdir
from random import shuffle
from tempfile import NamedTemporaryFile
from time import sleep
from typing import Union

import pkginfo
import requests

from bucket_dict import LazyBucketDict
from utils import parallel


email = os.environ.get("EMAIL")
if not email:
    raise Exception("Please provide EMAIL=")
headers = {'User-Agent': f'Pypi Daily Sync (Contact: {email})'}


@dataclass
class Job:
    name: str
    ver: str
    filename: str
    pyver: str
    url: str
    nr: int
    bucket: str


@dataclass()
class Result:
    job: Job
    requires_dist: str
    provides_extras: str
    requires_external: str
    requires_python: str


class Retry(Exception):
    pass


def construct_url(name, pyver, filename: str):
    base_url = "https://files.pythonhosted.org/packages/"
    return f"{base_url}{pyver}/{name[0]}/{name}/{filename}"


def mine_wheel_metadata_full_download(job: Job) -> Union[Result, Exception]:
    print(f"Bucket {job.bucket} - Job {job.nr} - {job.name}:{job.ver}")
    for _ in range(5):
        try:
            with NamedTemporaryFile(suffix='.whl') as f:
                resp = requests.get(job.url, headers=headers)
                if resp.status_code == 404:
                    return requests.HTTPError()
                if resp.status_code in [503, 502]:
                    try:
                        resp.raise_for_status()
                    except:
                        traceback.print_exc()
                    raise Retry
                resp.raise_for_status()
                with open(f.name, 'wb') as f_write:
                    f_write.write(resp.content)
                metadata = pkginfo.get_metadata(f.name)
            return Result(
                job=job,
                requires_dist=metadata.requires_dist,
                provides_extras=metadata.provides_extras,
                requires_external=metadata.requires_external,
                requires_python=metadata.requires_python,
            )
        except Retry:
            sleep(10)
        except zipfile.BadZipFile as e:
            return e
        except Exception:
            print(f"Problem with {job.name}:{job.ver}")
            traceback.print_exc()
            raise


def is_done(dump_dict, pkg_name, pkg_ver, pyver, filename):
    try:
        dump_dict[pkg_name][pyver][pkg_ver][filename]
    except KeyError:
        return False
    else:
        return True


def get_jobs(bucket, pypi_dict:LazyBucketDict, dump_dict: LazyBucketDict):
    names = list(pypi_dict.by_bucket(bucket).keys())
    jobs = []
    for pkg_name in names:
        for ver, release_types in pypi_dict[pkg_name].items():
            if 'wheels' not in release_types:
                continue
            for filename, data in release_types['wheels'].items():
                pyver = data[1]
                if is_done(dump_dict, pkg_name, ver, pyver, filename):
                    continue
                url = construct_url(pkg_name, pyver, filename)
                jobs.append(dict(
                    name=pkg_name, ver=ver, filename=filename, pyver=pyver,
                    url=url, bucket=bucket))
    shuffle(jobs)
    return [Job(**j, nr=idx) for idx, j in enumerate(jobs)]


def sort(d: dict):
    res = {}
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            res[k] = sort(v)
        else:
            res[k] = v
    return res


def decompress(d):
    for name, pyvers in d.items():
        for pyver, pkg_vers in pyvers.items():
            for pkg_ver, fnames in pkg_vers.items():
                for fn, data in fnames.items():
                    if isinstance(data, str):
                        key_ver, key_fn = data.split('@')
                        try:
                            pkg_vers[key_ver][key_fn]
                        except KeyError:
                            print(f"Error with key_ver: {key_ver} , key_fn: {key_fn}")
                            exit()
                        fnames[fn] = pkg_vers[key_ver][key_fn]


def compress(dump_dict):
    decompress(dump_dict)
    # sort
    for k, v in dump_dict.items():
        dump_dict[k] = sort(v)
    for name, pyvers in dump_dict.items():
        for pyver, pkg_vers in pyvers.items():

            all_fnames = {}
            for pkg_ver, fnames in pkg_vers.items():
                for fn, data in fnames.items():
                    for existing_key, d in all_fnames.items():
                        if data == d:
                            fnames[fn] = existing_key
                            break
                    if not isinstance(fnames[fn], str):
                        all_fnames[f"{pkg_ver}@{fn}"] = data


def exec_or_return_exc(func, job):
    try:
        return func(job)
    except Exception as e:
        traceback.print_exc()
        return e


def main():
    dump_dir = sys.argv[1]
    workers = int(os.environ.get('WORKERS', "1"))
    pypi_fetcher_dir = os.environ.get('pypi_fetcher')
    print(f'Index directory: {pypi_fetcher_dir}')
    assert isdir(pypi_fetcher_dir)
    for bucket in LazyBucketDict.bucket_keys():
        print(f"Begin wit bucket {bucket}")
        pypi_dict = LazyBucketDict(f"{pypi_fetcher_dir}/pypi")
        dump_dict = LazyBucketDict(dump_dir, restrict_to_bucket=bucket)
        jobs = list(get_jobs(bucket, pypi_dict, dump_dict))
        if not jobs:
            continue
        print(f"Starting batch with {len(jobs)} jobs")
        func = mine_wheel_metadata_full_download
        if workers > 1:
            def f(job):
                return exec_or_return_exc(func, job)
            result = parallel(f, (jobs,), workers=workers)
        else:
            result = [exec_or_return_exc(func, job) for job in jobs]
        for r in result:
            if isinstance(r, Exception):
                continue
            name = r.job.name
            ver = r.job.ver
            pyver = r.job.pyver
            fn = r.job.filename
            if name not in dump_dict:
                dump_dict[name] = {}
            if pyver not in dump_dict[name]:
                dump_dict[name][pyver] = {}
            if ver not in dump_dict[name][pyver]:
                dump_dict[name][pyver][ver] = {}
            dump_dict[name][pyver][ver][fn] = {}
            for key in ('requires_dist', 'provides_extras', 'requires_external', 'requires_python'):
                val = getattr(r, key)
                if val:
                    dump_dict[name][pyver][ver][fn][key] = val
        compress(dump_dict)
        dump_dict.save()


if __name__ == "__main__":
    main()
