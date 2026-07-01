#!/usr/bin/env python

import os
import pathlib
import tempfile as tf

class SystemSolver:
    """
    This class is a generic class to
    run specific types of models such as
    ODE and boolean
    """

    def __init__(self, inputfile, parameter):
        self.inputfile = inputfile
        self.parameter = parameter
        self.status = "not started"

    def Readfile(self):
        """
        General read method, reimplement in
        subclasses
        """
        with open(self.inputfile) as fp: self.root = fp.read()

    def Createtempfile(self, tempdir = None): #None
        if not tempdir:
            tempdir = os.path.join(pathlib.Path(__file__).parent.resolve().as_posix(),'tmp') # parent.resolve()
            print tempdir
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        fp = tf.NamedTemporaryFile(delete=False, dir = tempdir)
        self.tmpfile = fp.name
        self.output = self.tmpfile + ".out"

    def Writefile(self):
        """
        General write method reimplement
        in subclasses
        """
        with open(self.tmpfile,"w") as fp: fp.write(self.root)
        self.status = "ready"

    def Solve(self):
        """
        General solver class reimplement
        in subclasses
        """
        with open(self.output, "w") as fp: fp.write(self.root)

    def Cleanup(self):
        """
        Cleans up the temporary files
        """
        if os.path.exists(self.tmpfile):
            istatus = os.remove(self.tmpfile)
        if os.path.exists(self.output):
            ostatus = os.remove(self.output)


if __name__ == '__main__':
    solver = SystemSolver("Test.in", "Hello")
    solver.Readfile()
    solver.Createtempfile()
    solver.Writefile()
    solver.Solve()
    solver.Cleanup()
