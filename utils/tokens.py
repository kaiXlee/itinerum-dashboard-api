#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Kyle Fitzsimmons, 2017
from hashids import Hashids
import time


### REGISTRATION SHORTCODE GENERATOR AND VALIDATOR
# This function only checks whether token was issued with matching salt in valid timespan.
# It should be improved by building a mechanism to disable tokens that have been used.
def generate_registration_token(salt, min_length=0):
    hashids = Hashids(salt=salt, min_length=min_length)
    now = int(time.time())
    return hashids.encode(now)


def validate_registration_token(token, salt, expiration=0):
    hashids = Hashids(salt=salt)
    result = hashids.decode(token)
    if len(result) == 1:
        then, = result
        now = int(time.time())
        if expiration and (now - int(then)) < expiration:
            return True
    return False
