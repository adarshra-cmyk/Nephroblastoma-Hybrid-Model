#!/usr/bin/env python

import os, sys, json
import pickle, errno

def Make_Directory(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
