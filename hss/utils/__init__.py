#!/usr/bin/env python

import os, platform

def Create_Dir(path):
    """
    Create a new directory with provided
    path information
    """
    
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path): pass
        else: raise

def byteify(input):
    """
    This function change json unicode output to ascii
    Source- http://stackoverflow.com/a/13105359
    """

    if isinstance(input, dict):
        return dict((byteify(key),byteify(value)) for key,value in input.iteritems())
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def find_executable(path):
    """
    Obtains executable based on the
    architecture of the platform
    """
    arch = platform.architecture()[0]
    copasi_executable = os.path.join(path, arch, "CopasiSE")

    return copasi_executable
