#!/usr/bin/env python

import os, pickle, base64
import itertools
import StringIO
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import numpy as np
import operator

divlist = lambda lst, fac : [ elem/float(fac) for elem in lst ]
index = lambda data, end_time : np.where(data[:,0] == end_time*60*60)[0][0] if end_time != 'end' else -1

class PlotSweepOde:
    """
    Class to generate plots for specific
    parameter sweep conditions
    """
    def __init__(self, sweep_id, runsweeps, plot_params, control_sweep):
        self.sweep_id = sweep_id
        self.runsweeps = runsweeps
        self.plot_params = plot_params
        self.control_sweep = control_sweep
        self.plot_data = []
        self.plots = { key : {} for key in self.plot_params }
        self.plottext = {}

    def get_data(self):
        self.control_data = { "Time" : self.control_sweep["data"]["Time"] }
        self.control_data.update({ key : self.control_sweep["data"][key] for key in self.plot_params })
        for runsweep in self.runsweeps:
            sweep_data = { "Time" : runsweep["data"]["Time"] }
            sweep_data.update({ key : runsweep["data"][key] for key in self.plot_params })
            self.plot_data.append({ "scan_label" : self.__scan_label(runsweep["parameter"]), "sweep_data" : sweep_data })

    def __scan_label(self, parameter):
        param_list = []
        for elem in parameter:
            param_list.append("%s(%s) = %2.2f" % (elem["substitute"]["species"], elem["substitute"]["compartment"], elem["value"]))
        self.scan_label = ', '.join(param_list)

        return self.scan_label

    def timecourse(self, plot_param, end_time = 'end'):
        fig = plt.figure()
        legendstr = []
        for elem in self.plot_data:
            data = np.transpose(np.array([elem["sweep_data"]["Time"], elem["sweep_data"][plot_param]]))
            elem_index = index(data, end_time)
            legendstr.append(elem["scan_label"])
            p = plt.plot(divlist(elem["sweep_data"]["Time"][0:elem_index], 60), elem["sweep_data"][plot_param][0:elem_index])
        plt.xlabel("Time(mins)", fontsize = 14)
        plt.ylabel("%s Conc (nM)" % plot_param.replace('_', ' '), fontsize = 14)
        plt.tick_params(axis = 'both', which = 'major', labelsize = 12)
        plt.legend(legendstr)
        self.plottext["timecourse"] = ', '.join(legendstr)

        return fig
        

    def integrate(self, data, time_index, norm_value = 1.0):
        """
        Integrates time course data for a particular species
        at a specified time
        data is a N X 2 numpy array containing the time and
        species concentration.
        End time is assumed in hours
        """
        end_time_secs = data[time_index, 0]
        avg = np.trapz(data[0:time_index, 1], x = data[0:time_index, 0])/(norm_value*end_time_secs)

        return avg

    def barplot(self, plot_param, end_time='end', conc_unit = 'nM', normalization = "max"):
        """
        Plots the barplot for specified parameter and end time
        interval
        """
        fig = plt.figure()
        integrated_avg = []
        initial_values = []
            
        if normalization == "control":
            control_data = np.transpose(np.array([self.control_data["Time"], self.control_data[plot_param]]))
            control_index = index(control_data, end_time)
            control_average = self.integrate(control_data, control_index)
            integrated_avg.append(control_average/control_average)
        for ii,elem in enumerate(self.plot_data):
            data = np.transpose(np.array([elem["sweep_data"]["Time"], elem["sweep_data"][plot_param]]))
            elem_index = index(data, end_time)
            if normalization == "max":
                norm_value = np.max(data[0:elem_index, 1])
            elif normalization == "control":
                norm_value = control_average
            else:
                norm_value = 1.0
                
            initial_values.append("%s: %s" % (str(ii + 1), elem["scan_label"]))
            integrated_avg.append(self.integrate(data, elem_index, norm_value = norm_value))
        xval = np.arange(len(integrated_avg))
        p = plt.bar(xval + 1, integrated_avg, tick_label = [elem + 1 for elem in xval], width = 0.35, align = 'center')
        plt.ylabel("%s Conc (%s)" % (plot_param, conc_unit), fontsize = 14)
        plt.xlabel("Scan parameters")
        #plt.text(0.9, 0.9, '\n'.join(initial_values))
        control_str = "(Control)" if normalization == "control" else "" 
        self.plottext["bar"] = initial_values[0] + " " + control_str + ", " + ', '.join(initial_values[1:])

        return fig

    def store_figstr(self, fig, plottype, plot_param, end_time = 48):
        """
        Stores an appropriate plot object
        """
        self.plots.setdefault(plot_param, {})
        self.plots[plot_param].setdefault(plottype, {})
        for key in ["pngstr","epstr","scan_label"]:
            self.plots[plot_param][plottype].setdefault(key, {})
        self.plots[plot_param][plottype]["pngstr"][str(end_time) + "h"] = self.__figure_text(fig)
        self.plots[plot_param][plottype]["epstr"][str(end_time) + "h"] = self.__figure_text(fig, filetype = 'eps')
        self.plots[plot_param][plottype]["scan_label"][str(end_time) + "h"] = self.plottext[plottype]
        #self.plots[plot_param][plottype]["fig"] = fig

    def save_fig(self, fig, plot_param, plottype, outdir = "figures", end_time=48):
        """
        Saves the figure object as a file
        """
        pngfile = os.path.join(outdir, "ODE_%s_%s_%s_%sh.png" % (plot_param.replace(' ','_'), plottype, self.sweep_id, end_time))
        pdffile = os.path.join(outdir, "ODE_%s_%s_%s_%sh.pdf" % (plot_param.replace(' ','_'), plottype, self.sweep_id, end_time))
        fig.savefig(pngfile)
        fig.savefig(pdffile, dpi = 300)

    def __figure_text(self, fig, filetype = "png"):
        """
        Converts a matplotlib plot object into string
        representation
        """
        imgdata = StringIO.StringIO()

        fig.savefig(imgdata, format = filetype, bbox_inches="tight")
        imgdata.seek(0)

        if filetype == "png":
            figstr = base64.b64encode(imgdata.read())
        elif filetype == "eps":
            figstr = imgdata.read()
        else:
            raise Exception("Filetype %s not supported" % filetype)

        return figstr

    def save_instance(self, outdir="data"):
        """
        Saves a plot instance as a pickle
        """
        with open(os.path.join(outdir, "Sweep_Instance_%s.pickle" % self.sweep_id), "wb") as fp: pickle.dump(self, fp)

    def save_figstr(self, outdir = "figures"):
        """
        Save the plot figure strings as pickle file
        to enable loading and generate reports
        """
        with open(os.path.join(outdir, "Ode_Plot_Figures_%s.pickle" % self.sweep_id), "wb") as fp: pickle.dump({ "sweep_id" : self.sweep_id, "plots" : self.plots }, fp)

    def close_fig(self, fig = "all"):
        """
        Closes the figure object
        """
        plt.close(fig)
        

class PlotSweepBool:
    """
    Class to generate plots for boolean for specific parameter
    sweep conditions.
    """

    def __init__(self, sweep_id, runsweeps, plot_params):
        self.sweep_id = sweep_id
        self.runsweeps = runsweeps
        self.plot_params = plot_params
        self.plot_data = []
        self.plots = { key : {} for key in self.plot_params }
        self.plottext = {}
        
    def get_data(self):
        for runsweep in self.runsweeps:
            sweep_data = {}
            sweep_data.update({ key : runsweep["data"][key] for key in self.plot_params })
            sweep_data["steps"] = list(range(len(sweep_data[sweep_data.keys()[0]])))
            self.plot_data.append({ "scan_label" : self.__scan_label(runsweep["parameter"]), "sweep_data" : sweep_data })
            
    def __scan_label(self, parameter):
        param_list = []
        for node, status in parameter["states"].items():
            param_list.append("%s = %d" % (node, status))
        self.scan_label = ', '.join(param_list)

        return self.scan_label

    def statusplots(self, plot_param):
        fig = plt.figure()
        legendstr = []
        marker = itertools.cycle(('+','o','*','<'))
        for elem in self.plot_data:
            p = plt.plot(elem["sweep_data"]["steps"], elem["sweep_data"][plot_param], marker = marker.next())
            legendstr.append(elem["scan_label"])
        plt.xlabel("Steps", fontsize = 14)
        plt.ylabel("%s Status" % plot_param, fontsize = 14)
        plt.legend(legendstr)

        self.plottext["statusplots"] = ", ".join(legendstr)

        return fig

    def statustable(self, plot_params = "all"):
        if plot_params == "all":
            headers = ",".join(["Step"] + sorted(self.runsweeps[0]["data"].keys()))
        else:
            headers = ",".join(["Steps"] + plot_params)

        tablestr = [headers]
        for ii, runsweep in enumerate(self.runsweeps):
            sorted_data = sorted(runsweep["data"].items(), key = lambda x : x[0])
            tablestr.append("Sweep %i" % ii)
            for state in range(len(sorted_data[0][-1])):
                row = [str(state + 1)] + [ str(elem[-1][state]) for elem in sorted_data ]
                tablestr.append(','.join(row))

        return "\n".join(tablestr)

    def save_fig(self, fig, plot_param, outdir = "figures"):
        
        pngfile = os.path.join(outdir, "Bool_%s_%s.png" % (plot_param.replace(' ','_'), self.sweep_id))
        pdffile = os.path.join(outdir, "Bool_%s_%s.pdf" % (plot_param.replace(' ','_'), self.sweep_id))
        fig.savefig(pngfile)
        fig.savefig(pdffile, dpi = 300)

    def store_figstr(self, fig, plot_param):
        """
        Stores an appropriate plot object
        """
        self.plots.setdefault(plot_param, {})
        for key in ["pngstr","epstr","scan_label"]:
            self.plots[plot_param].setdefault(key, {})
        self.plots[plot_param]["pngstr"] = self.__figure_text(fig)
        self.plots[plot_param]["epstr"] = self.__figure_text(fig, filetype = 'eps')
        self.plots[plot_param]["scan_label"] = self.plottext

    def __figure_text(self, fig, filetype = "png"):
        """
        Converts a matplotlib plot object into string
        representation
        """
        imgdata = StringIO.StringIO()

        fig.savefig(imgdata, format = filetype, bbox_inches="tight")
        imgdata.seek(0)

        if filetype == "png":
            figstr = base64.b64encode(imgdata.read())
        elif filetype == "eps":
            figstr = imgdata.read()
        else:
            raise Exception("Filetype %s not supported" % filetype)

        return figstr

    def save_figstr(self, outdir = "figures"):
        """
        Save the plot figure strings as pickle file
        to enable loading and generate reports
        """
        with open(os.path.join(outdir, "Bool_Plot_Figures_%s.pickle" % self.sweep_id), "wb") as fp: pickle.dump({ "sweep_id" : self.sweep_id, "plots" : self.plots }, fp)

    def close_fig(self, fig = "all"):
        """
        Closes the figure object
        """
        plt.close(fig)

if __name__ == '__main__':
    execfile("runsweep.py")
    plot_param = ['STATc-Cytoplasm', 'pSTATn-Nucleus']
    plot_param = ['STATc-Compartment', 'pSTATn_pSTATn-Compartment']
    ps = PlotSweep(sweepers, plot_param)
    ps.get_data()
    for elem in plot_param:
        fig = ps.timecourse(elem)
        ps.store_fig(fig, "timecourse", elem)
        fig = ps.barplot(elem)
        ps.store_fig(fig, "bar", elem)
    
