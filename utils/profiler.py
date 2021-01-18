#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
import time


def timeit(func):
    def timed(*args, **kwargs):
        t0 = time.time()
        result = func(*args, **kwargs)
        t1 = time.time()

        print('{func}(args, kwargs): {time} sec'.format(
            func=func.__name__, time=t1-t0))
        return result
    return timed