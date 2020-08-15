from bounded_pool_executor import BoundedThreadPoolExecutor, BoundedProcessPoolExecutor


def parallel(func, args_list, workers=10, use_processes=False):
    if use_processes:
        Executor = BoundedProcessPoolExecutor
    else:
        Executor = BoundedThreadPoolExecutor
    with Executor(max_workers=workers) as tpe:
        res = tpe.map(func, *args_list)
        return list(res)
