#!/usr/bin/env python

import os, operator, csv
import json
import sweep
import subprocess
from system_solver import SystemSolver

listsum = lambda lst, val : map(operator.add, lst, [val]*len(lst))
change_ext = lambda filename, ext : os.path.splitext(filename)[0] + ext
CopasiPath = "CopasiSE"

class OdeSolver(SystemSolver):
    """
    This class solves systems models using by calling
    Copasi as an external solver
    """
    def __init__(self, inputfile, parameter, conv = 1.0):
        SystemSolver.__init__(self, inputfile, parameter)
        self.conv = conv
        self.current_time = 0
        self.num_runs = 0
        self.num_data = 0
        self.interface_parameter = []
        self.interface_data = []
        self.job_status = "not started"

    def Readfile(self, filename = None):
        """
        Reads a copasi file into a root
        element
        """
        if not filename:
            self.root, self.xmlstring = sweep.Generate_Xml(self.inputfile)
        else:
            self.root, self.xmlstring = sweep.Generate_Xml(filename)

    def Change_Parameters(self):
        """
        Changes the sweep parameters
        """
        for param in self.parameter:
            oldval, newval = sweep.SetCpsValues(self.root, param, conv = self.conv)
            param["value_change"] = (float(oldval)/self.conv, float(newval)/self.conv)
        for param in self.interface_parameter:
            oldval, newval = sweep.SetCpsValues(self.root, param, conv = self.conv)
            param["value_change"] = (float(oldval)/self.conv, float(newval)/self.conv)
        Outfilename = self.change_report()

    def change_report(self, XPathstr = ".//*[@type='timeCourse']", update = "true"):
        Task_Time_Course = sweep.Get_Elem(self.root, XPathstr)
        Outfilename = change_ext(self.tmpfile, ".csv")
        Task_Time_Course = sweep.Set_Elem(Task_Time_Course, "updateModel", update)
        Report = sweep.Set_Elem(Task_Time_Course[0], "target", Outfilename)
        self.update = update
        self.output = Outfilename

        return Outfilename

    def Initialize_Data(self):

        self.header = sweep.Get_Headers(self.root, ".//Table")
        self.data = { key : [] for key in self.header }
        self.data_indices = []

    def __get_duration(self, XPathstr = ".//*[@name='Duration']"):
        Duration = sweep.Get_Elem(self.root, XPathstr).get("value")
        return float(Duration)

    def Writefile(self):
        sweep.Write_File(self.root, self.tmpfile)
        self.status = "ready"

    def Solve(self, copasipath=CopasiPath):
        out = err = ''
        Copasi_Command = copasipath + ' --verbose ' + self.tmpfile + ' -s ' + self.tmpfile
        self.job_status = "Running"
        p = subprocess.Popen(Copasi_Command,shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for lines in iter(p.stdout.readline,''):
            out += lines.rstrip()
        for lines in iter(p.stderr.readline,''):
            err += lines.rstrip()
        streams = p.communicate()
        self.num_runs += 1
        self.job_status = "completed"
        self.error = (out, err)

    def reinitialize(self):
        """
        Reinitializes a model initial state
        """
        self.Cleanup()
        self.Readfile()
        self.Createtempfile()


    def Get_Data(self):
        """
        Extracts data for a particular run and appends to
        the input dictionary
        """

        if self.job_status != "completed":
            raise Exception("Job still %s for %s" % (self.job_status, self.tmpfile))
        if self.num_data >= self.num_runs:
            raise Exception("Data already updated with latest run")
        if self.num_data < self.num_runs - 1:
            raise Exception("Data lagging by more than one runs, restart simulation")

        start_index = len(self.data["Time"]) - 1 if len(self.data["Time"]) > 0 else 0
        with open(self.output) as fp:
            reader = csv.DictReader(fp, fieldnames = self.header)
            reader.next() # skip header # there are better ways to do this
            for ii, row in enumerate(reader):
                for key in row:
                    if key == "Time":
                        self.data[key].append(self.current_time + float(row[key]))
                    else:
                        self.data[key].append(float(row[key]))
        self.current_time += self.__get_duration()
        end_index = len(self.data["Time"]) - 1 if len(self.data["Time"]) > 0 else 0
        self.data_indices.append((start_index, end_index))
        if self.num_runs == 1:
            self.initial_indices = (start_index, end_index)
        self.interface_data.append(self.interface_parameter)
        self.num_data += 1

    def Initial_Run(self, initial_changes = [], updatemodel = True):
        """
        Performs an initial run of the model using
        the provided data
        """
        self.parameter.extend(initial_changes)
        self.Readfile()
        self.Initialize_Data()
        self.Createtempfile()
        self.Change_Parameters()
        self.Writefile()
        self.Solve()
        self.Get_Data()
        if updatemodel:
            self.Readfile(filename = solver.tmpfile)
            self.parameter = []
        self.Cleanup()

    def Equilibrium_Run(self, updatemodel = True):
        """
        Performs an equilibrium run of the model
        """
        self.Createtempfile()
        self.Change_Parameters()
        self.Writefile()
        self.Solve()
        self.Get_Data()
        if updatemodel:
            self.Readfile(filename = solver.tmpfile)
        self.Cleanup()


if __name__ == '__main__':

    #inputfile = "../io/ChenBIOMD0000000019_ErbB-WT_orig_norules.cps"
    conv = 602214179000000
    inputfile = "../../tests/ErbB4-JAK2-STAT5_Yamda_Combined_Exec.cps"
    with open("Parameter2.json") as fp: parameter = json.load(fp).values()
    oderun = OdeSolver(inputfile, parameter, conv = conv)
    oderun.Readfile()
    oderun.Initialize_Data()
    oderun.Createtempfile()
    oderun.Change_Parameters()
    Outfilename = oderun.change_report()
    oderun.Writefile()
    oderun.Solve()
    oderun.Get_Data()
    oderun.Cleanup()
