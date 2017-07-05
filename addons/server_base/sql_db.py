# -*- coding: utf-8 -*-

import psycopg2.extensions

#+KGB INT, BIGINT TO python INT to avoid long Python int on 64bit ubuntu server is 64bit, no need for long
def force_int(symb, cr):
    if symb is None:
        return None
    return int(symb)
psycopg2.extensions.register_type(
    psycopg2.extensions.new_type((20,23,), 'int',
                                 lambda value, curs: int(value) if value is not None else None))

