import base64
import os
import sys
import traceback
import xmlrpc.client
from time import sleep
from urllib.parse import quote

import requests
import utils
from bucket_dict import LazyBucketDict
from requests import HTTPError

base_url = "https://pypi.org/pypi"
session = requests.Session()
email = os.environ.get("EMAIL")
if not email:
    raise Exception("Please provide EMAIL=")
headers = {'User-Agent': f'Pypi Daily Sync (Contact: {email})'}


def urlencode(s):
    return quote(s, safe='/ ')


def hash_hex_to_base64(hash):
    return base64.b64encode(bytes.fromhex(hash)).decode()


def all_packages():
    xmlclient = xmlrpc.client.ServerProxy(base_url)
    return xmlclient.list_packages_with_serial()


def pkg_meta(name):
    resp = session.get(f"{base_url}/{name}/json", headers=headers)
    resp.raise_for_status()
    return resp.json()


def select_favorite_sdist_release(sdist_releases):
    """
    Selects one sdist from a list while prioritizing the file suffixes
    (tar.gz, tgz, zip, tar.bz2) (left == better).
    If multiple filenames with same suffix exist, the shortest filename is picked
    """
    sdist_releases = list(sdist_releases)
    f_types = ('tar.gz', '.tgz', '.zip', '.tar.bz2')
    compatible_releases = filter(lambda r: any(r['filename'].endswith(end) for end in f_types),
                                 sdist_releases)
    sorted_releases = sorted(compatible_releases,
                             key=lambda r: next(i for i, t in enumerate(f_types) if r['filename'].endswith(t)))
    if not sorted_releases:
        return []
    return sorted_releases[0]


def save_pkg_meta(name, pkgs_dict):
    api_success = False
    while not api_success:
        try:
            meta = pkg_meta(name)
            api_success = True
        except HTTPError as e:
            if e.response.status_code == 404:
                return
        except:
            traceback.print_exc()
            print("Warning! problems accessing pypi api. Will retry in 10s")
            sleep(10)
    releases_dict = {}
    # iterate over versions of current package
    for release_ver, release in meta['releases'].items():
        release_ver = release_ver.strip()
        sdists = filter(lambda file: file['packagetype'] in ["sdist"], release)
        sdist = select_favorite_sdist_release(sdists)
        wheels = list(filter(lambda file: file['packagetype'] in ["bdist_wheel"], release))
        if not (sdist or wheels):
            continue
        releases_dict[release_ver] = {}
        if sdist:
            releases_dict[release_ver]['sdist'] = [
                hash_hex_to_base64(sdist['digests']['sha256']),
                urlencode(sdist['filename']),
            ]
        if wheels:
            releases_dict[release_ver]['wheels'] = {
                wheel['filename']: (
                    hash_hex_to_base64(wheel['digests']['sha256']),
                    wheel['python_version'])
                for wheel in wheels
            }
    if releases_dict:
        pkgs_dict[name.replace('_', '-').lower()] = releases_dict


def crawl_pkgs_meta(packages, target_dir, workers):
    pkgs_dict = LazyBucketDict(target_dir)
    args_list = [(name, pkgs_dict) for name in packages]
    if workers > 1:
        utils.parallel(save_pkg_meta, zip(*args_list), workers=workers)
    else:
        [save_pkg_meta(*args) for args in args_list]
    pkgs_dict.save()


def names_in_buckets():
    in_buckets = {}
    for name in all_packages():
        bucket = LazyBucketDict.bucket(name.replace('_', '-').lower())
        if bucket not in in_buckets:
            in_buckets[bucket] = []
        in_buckets[bucket].append(name)
    return in_buckets


def main():
    target_dir = sys.argv[1]
    workers = int(os.environ.get('WORKERS', "1"))
    for i, names in enumerate(names_in_buckets().values()):
        print(f"crawling bucket nr. {i}")
        crawl_pkgs_meta(names, target_dir, workers=workers)


if __name__ == "__main__":
    main()
