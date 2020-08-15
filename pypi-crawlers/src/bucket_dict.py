import json
import os
from _sha256 import sha256
from collections import UserDict, OrderedDict


class LazyBucketDict(UserDict):

    def __init__(self, directory, data=None, restrict_to_bucket: str = None):
        super().__init__()
        self._restrict_to_bucket = restrict_to_bucket
        self.directory = directory
        self.data = {}
        if data:
            for key, val in data.items():
                self.__setitem__(key, val)

    def __getitem__(self, key):
        bucket = self._bucket_secure(key)
        self.ensure_bucket_loaded(bucket)
        return self.data[bucket][key]

    def __setitem__(self, key, val):
        bucket = self._bucket_secure(key)
        self.ensure_bucket_loaded(bucket)
        self.data[bucket][key] = val

    def __contains__(self, key):
        bucket = self._bucket_secure(key)
        self.ensure_bucket_loaded(bucket)
        return key in self.data[bucket]

    def __delitem__(self, key):
        bucket = self._bucket_secure(key)
        self.ensure_bucket_loaded(bucket)
        del self.data[bucket][key]

    def items(self):
        for key in self.keys():
            yield key, self[key]

    @staticmethod
    def bucket_keys():
        hexdigits = "0123456789abcdef"
        for a in hexdigits:
            for b in hexdigits:
                yield a + b

    def by_bucket(self, bucket):
        self.ensure_bucket_loaded(bucket)
        return self.data[bucket]

    def keys(self, bucket=None):
        if bucket:
            if self._restrict_to_bucket and bucket != self._restrict_to_bucket:
                raise Exception(
                    f'Attempt to access data in bucket {bucket}, while access is restricted to {self._restrict_to_bucket}')
            self.ensure_bucket_loaded(bucket)
            for k in self.data[bucket].keys():
                yield k
        else:
            if self._restrict_to_bucket:
                buckets = [self._restrict_to_bucket]
            else:
                buckets = self.bucket_keys()
            for bucket in buckets:
                self.ensure_bucket_loaded(bucket)
                for k in self.data[bucket].keys():
                    yield k

    @staticmethod
    def bucket(key):
        return sha256(key.encode()).hexdigest()[:2]

    def _bucket_secure(self, key):
        b = self.bucket(key)
        restricted = self._restrict_to_bucket
        if restricted and b != restricted:
            raise Exception(f'Attempt to access data in bucket {b}, while access is restricted to {restricted}')
        return b

    def save_bucket(self, bucket, directory_path):
        self.ensure_bucket_loaded(bucket)
        save = OrderedDict(sorted(self.data[bucket].items(), key=lambda item: item[0]))
        with open(f"{directory_path}/{bucket}.json", 'w') as f:
            json.dump(save, f, indent=2)

    def save(self):
        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)
        for bucket in self.data.keys():
            self.save_bucket(bucket, self.directory)

    def load_bucket(self, bucket):
        file = f"{self.directory}/{bucket}.json"
        if not os.path.isfile(file):
            self.data[bucket] = {}
        else:
            with open(file) as f:
                self.data[bucket] = json.load(f)

    def ensure_bucket_loaded(self, bucket):
        if bucket not in self.data:
            self.load_bucket(bucket)
