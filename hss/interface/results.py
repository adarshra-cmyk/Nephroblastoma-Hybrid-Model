#!/usr/bin/env python

import json, pickle
import os
import sys

from collections import OrderedDict
from pprint import pprint
import numpy as np
from optparse import OptionParser

script_dirs = ['visualization']
for dirs in script_dirs:
    sys.path.append(os.path.abspath("../%s" % dirs))

import plots

def Time_Course_Average(Species = ["ERK_PP-cytoplasm","AKT_P_P-cytoplasm","Raf_P-cytoplasm"]):
    """
    Calculates the average time course over the sweep elements
    """
    data = { key : {} for key in Species }
    data["Time"] = {}
    data_indices = {}
    for key, value in Sweep_Data.items():
        combkey = (value["args"][3][0]["value"], value["args"][-1])
        val = data_indices.setdefault(combkey, [])
        data_indices[combkey].append(Model_Data[key]["chenode"]["data_indices"])
        for k, v in data.items():
            val = v.setdefault(combkey, [])
            v[combkey].append(Model_Data[key]["chenode"]["data"][k])
    for key, value in data_indices.items():
        if value[1:] != value[:-1]:
            raise Exception("Indices are not the same")
        else:
            data_indices[key] = value[0]

    dataavg = { key : {} for key, value in data.items() }
    for key, value in data.items():
        for k, v in value.items():
            minlen = min([ len(elem) for elem in v ])
            for ii, elem in enumerate(v):
                v[ii] = elem[:minlen]
            dataavg[key][k] = np.nanmean(v, axis = 0)
    #dataavg = { key : { k : np.nanmean(v, axis = 0) for k,v in value.items() } for key, value in data.items() }
    integral_avg = { key : {} for key in dataavg }
    for key, value in dataavg.items():
        for k,v in value.items():
            val = integral_avg[key].setdefault(str(k), [])
            #for ii in range(0, len(dataavg["Time"][k]), 24):
            for istart, iend in data_indices[k]:
                #index = ii if ii == 0 else ii + 1
                if key != "Time":
                    integral_avg[key][str(k)].append(np.trapz(v[istart:iend],dataavg["Time"][k][istart:iend])/(dataavg["Time"][k][iend] - dataavg["Time"][k][istart]))
                    #integral_avg[key][str(k)].append(np.trapz(v[index:24+index],dataavg["Time"][k][index:24+index])/(dataavg["Time"][k][25] - dataavg["Time"][k][0]))
                else:
                    integral_avg[key][str(k)].append(dataavg["Time"][k][istart])
    #minlen = min([len(elem) for elem in integral_avg["Time"].values()])
    #for key, values in integral_avg.items():
    #    for k, v in values.items():
    #        integral_avg[key][k] = v[:minlen]

    return integral_avg


def Sweep_Average():
    """
    Calculates the average cell fate over sweep elements
    """
    Sweep_Info = {}
    Cell_Fate_List = { "cell_death" : [], "cell_growth" : [], "cell_senescence" : [], "net_cell_growth" : [] }

    for key, value in Sweep_Data.items():
        combkey = (value["args"][3][0]["value"], value["args"][-1])
        val = Sweep_Info.setdefault(combkey, {})
        cell_fates = Model_Data[key]["choibool"]["cell_fate_lookup"]
        cell_fate_probabilities = { k : float(v)/sum(cell_fates.values()) for k, v in cell_fates.items() }
        cell_fate_probabilities["net_cell_growth"] = cell_fate_probabilities["cell_growth"] - cell_fate_probabilities["cell_death"]
        for k, v in cell_fate_probabilities.items():
            val = Sweep_Info[combkey].setdefault(k, [])
            Sweep_Info[combkey][k].append(v)
        val = Sweep_Info[combkey].setdefault("Cases", [])
        Sweep_Info[combkey]["Cases"].append(key)

     
    print Sweep_Info.items()

    for key, value in Sweep_Info.items():
        for k, v in value.items():
            if k != "Cases":
                Cell_Fate_List[k].append(sum(v)/len(v))

    return Sweep_Info, Cell_Fate_List

if __name__ == '__main__':


    usage = "usage: %prog [options]"
    parser = OptionParser(usage = usage)
    parser.set_defaults(
       run_prefix="lifer", 
       patient = "5XIHQG",
       cases = ["Control_Rad_15Gy", "Actinomycin_Rad_15Gy", "Dox_Rad_15Gy", "Vincristine_Rad_15Gy", 
                "Actinomycin_Dox_Rad_15Gy", "Actinomycin_Vincristine_Rad_15Gy", "Dox_Vincristine_Rad_15Gy",
                "Actinomycin_Dox_Vincristine_Rad_15Gy"])
       #cases = ["Control", "Control_Rad_15Gy", "Control_Rad_25Gy"]) 
       #cases =  ["Control", "Actinomycin", "Dox", "Vincristine", 
       #          "Actinomycin_Dox", "Actinomycin_Vincristine", "Dox_Vincristine",
       #          "Actinomycin_Dox_Vincristine"])
    parser.add_option("-p", "--patient-id", dest="patient")
    parser.add_option("-d", "--drug-cases", dest="cases")
    parser.add_option("-r", "--run-prefix", dest="run_prefix")
    (options, args) = parser.parse_args()
    
    patient = options.patient
    cases = options.cases
    if not isinstance(cases, list):
        cases = cases.replace(" ","").split(",")
    run_prefix = options.run_prefix

    Cell_Fate_Patient_List = OrderedDict()
    Time_Course_Data = OrderedDict()
    Species = ["ERK_PP-cytoplasm","AKT_P_P-cytoplasm","Raf_P-cytoplasm","total_ERK_PP","total_AKT_PP"]
    flist = []

    for drug in cases:
        suffix = "%s_%s" % (patient, drug)
        if run_prefix:
            suffix = "%s_%s" % (run_prefix, suffix)

        Model_Data_File = "Model_Data_%s.pickle" % suffix
        Sweep_Data_File = "Sweepfile_%s.json" % suffix

        with open(Model_Data_File) as fp: Model_Data = pickle.load(fp)
        with open(Sweep_Data_File) as fp: Sweep_Data = json.load(fp)
        Sweep_Info, Cell_Fate_List = Sweep_Average()
        
        print drug, Cell_Fate_List
        Cell_Fate_Patient_List[patient + "_" + drug] = Cell_Fate_List
        Time_Course_Data[patient + "_" + drug] = Time_Course_Average(Species = Species)
        flist.append(plots.time_course_plot(patient, drug, Time_Course_Data[patient + "_" + drug]))

    print Cell_Fate_Patient_List
    f = plots.cell_fate_plot(patient, Cell_Fate_Patient_List)
    f = plots.Tumor_Volumes(lookup = True, drug = "Vincristine")
    f = plots.Tumor_Volumes(lookup = False, drug = "Vincristine")
