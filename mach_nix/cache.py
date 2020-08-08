from inspect import isgenerator

cache = {}


def cached(keyfunc=None):
    def cached_deco(func):
        def cache_wrapper(*args, **kwargs):
            args_save = keyf(args)
            key = (func, args_save, tuple(kwargs.items()))
            if key not in cache:
                result = func(*args, **kwargs)
                if isgenerator(result):
                    result = tuple(result)
                cache[key] = result
            return cache[key]
        return cache_wrapper

    keyf = (lambda x: x) if keyfunc is None else keyfunc
    return cached_deco

