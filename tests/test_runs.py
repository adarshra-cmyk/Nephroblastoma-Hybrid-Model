#!/usr/bin/env python

# Script to test the runs for different cases
from __future__ import print_function
import os
import json, pickle
import difflib, itertools
from pprint import pprint

def Convert_Indicator(indicator):
    """
    Converts the indicator into a form keyed by different
    cell fates
    """
    Indicators = {}
    for elem in indicator:
        key = tuple(elem for sublist in elem[0].items() for elem in sublist)
        Indicators[key] = elem[1]

    return Indicators

def Cell_Fate_Lookup(booldata, Indicators, Target_Nodes):
    """
    This function calculates cell fate from lookup table
    """
    Cell_Fates = { "cell_death" : [], "cell_growth" : [], "cell_senescence" : [] }
    Cell_Fates_Total = { "cell_death" : 0.0, "cell_growth" : 0.0, "cell_senescence" : 0.0 }
    total = 0.0

    for elem in booldata:
        for step in range(len(elem.values()[0])):
            key = []
            for node in Target_Nodes:
                key.extend([node, elem[node][step]])
            Cell_Fates_Total[Indicators[tuple(key)]] += 1
            total += 1
    Cell_Fate_Probabilities = { key : float(value)/total for key,value in Cell_Fates_Total.items() }

    return Cell_Fates_Total, Cell_Fate_Probabilities

def Cell_Fate(booldata, indicator, drug = "Control"):
    """
    This function calculates the cell fates independently after
    processing and operates on the whole list of data
    """
    Cell_Fates = { "cell_death" : [], "cell_growth" : [], "cell_senescence" : [] }
    Cell_Fates_Total = { "cell_death" : 0.0, "cell_growth" : 0.0, "cell_senescence" : 0.0 }
    total = 0.0

    for elem in booldata.values():
        nodestatus = elem["choibool"]["data"]
        #nodestatus = elem
        cell_death = 0
        cell_growth = 0
        cell_senescence = 0

        for step in range(len(nodestatus.values()[0])):
            status = False
            growth = False
            death = False
            for key, value in indicator.items():
                if all( nodestatus[k][step] == v for k, v in value.items() ):
                    if key == "cell_growth":
                        if death:
                            Cell_Fates_Total["cell_death"] -= 1
                            cell_growth -= 1
                            total -= 1
                        Cell_Fates_Total[key] += 1
                        cell_growth += 1
                        total += 1
                        status = True
                        growth = True
                        death = False
                        if drug == "Control":
                            break
                    else:
                        if growth:
                            Cell_Fates_Total["cell_growth"] -= 1
                            cell_growth -= 1
                            total -= 1
                        Cell_Fates_Total[key] += 1
                        cell_death += 1
                        total += 1
                        status = True
                        growth = False
                        death = True
                        if drug != "Control":
                            break
                        
            if not status:
                Cell_Fates_Total["cell_senescence"] += 1
                cell_senescence += 1
                total += 1
        Cell_Fates["cell_death"].append(cell_death)
        Cell_Fates["cell_growth"].append(cell_growth)
        Cell_Fates["cell_senescence"].append(cell_senescence)

    Cell_Fate_Probabilities = { key : float(value)/total for key,value in Cell_Fates_Total.items() }

    return Cell_Fates_Total, Cell_Fate_Probabilities

def Print_Sweeps():
    
    print("Sweep data arguments for Control")
    print(zip(Sweepdata_Control[index]["args"][1],Sweepdata_Control[index]["args"][2]))
    print("Sweep data arguments for Dox")
    print(zip(Sweepdata_Dox[index]["args"][1],Sweepdata_Dox[index]["args"][2]))

    print("Script output for Control:")
    print(Sweepdata_Control[index]["scriptout"])
    print("Script output for Dox:")
    print(Sweepdata_Dox[index]["scriptout"])

def Write_Nodes(indices):
    """
    Write the status of the various nodes in files
    """
    
    for ind in indices:
        booldata_control = Simulation_Data["Control"]["Model_Data"][ind]["choibool"]["data"]
        booldata_dox = Simulation_Data["Dox"]["Model_Data"][ind]["choibool"]["data"]
        with open(os.path.join(Parent_Dir, Patient_Id + "_" + "Logs", "%s_%s.out" % (Patient_Id, ind)), "a") as fp:
            fprint = lambda args : print(args, file = fp)
            fpprint = lambda args : pprint(args, stream = fp)
            fprint("Index = %s" % ind)
            fpprint(Sweepdata_Control[ind]["args"])
            fpprint(Sweepdata_Dox[ind]["args"])
            fprint("------------------")
            fprint("Drug Related Nodes")
            for key in Nodes:
                fprint("Control %s, %s, %s" % (key, str(booldata_control[key][:5]),str(booldata_control[key][-5:])))
                fprint("Dox %s, %s, %s" % (key, str(booldata_dox[key][:5]),str(booldata_dox[key][-5:])))
            fprint("------------------")
            fprint("Cell Fate Nodes")
            for key in CNodes:
                fprint("Control %s, %s, %s" % (key, str(booldata_control[key][:5]),str(booldata_control[key][-5:])))
                fprint("Dox %s, %s, %s" % (key, str(booldata_dox[key][:5]),str(booldata_dox[key][-5:])))
            fprint("------------------")
            fprint("Interface Nodes")
            for key in INodes:
                fprint("Control %s, %s, %s" % (key, str(booldata_control[key][:5]),str(booldata_control[key][-5:])))
                fprint("Dox %s, %s, %s" % (key, str(booldata_dox[key][:5]),str(booldata_dox[key][-5:])))
    
def Write_Diffs(indices):
   """
   Write the difference between two cases
   """
   for ind1, ind2 in itertools.combinations(indices, 2):
       with open(os.path.join(Parent_Dir, Patient_Id + "_" + "Logs", "%s_%s.out" % (Patient_Id, ind1))) as fp1, open(os.path.join(Parent_Dir, Patient_Id + "_" + "Logs", "%s_%s.out" % (Patient_Id, ind2))) as fp2:
           diff = difflib.unified_diff(fp1.readlines(), fp2.readlines(), fp1.name, fp2.name)
       with open(os.path.join(Parent_Dir, Patient_Id + "_" + "Logs", "%s_%s_%s.diff" % (Patient_Id, ind1, ind2)), "w") as fp:
           fp.writelines(diff)
   

if __name__ == '__main__':
    
    Patient_Id = "Control"
    Parent_Dir = "Temp_Data"
    Simulation_Data = { "Control" : {}, "Dox" : {} }
    Nodes = ["CDK1", "PTEN", "ATM", "TP53", "MDM2"]
    CNodes = ["CDK2","CASP9"]
    INodes = ["ERK_PP","AKT_P","Raf_P","PTEN"]
    index = "0"
    indices = ["24","20","1","9"]
        
    for Case in Simulation_Data:
        Sweepfile = os.path.join(Parent_Dir, Patient_Id + "_" + Case,
                             "Sweepfile_%s_%s.json" % (Patient_Id, Case))
        with open(Sweepfile) as fp: Simulation_Data[Case]["Sweepdata"] = json.load(fp)
        Simulation_Data[Case]["Sweepfile"] = Sweepfile
        Cell_Fate_File = os.path.join(Parent_Dir, Patient_Id + "_" + Case,
                             "Cell_Fates_%s_%s.json" % (Patient_Id, Case))
        with open(Cell_Fate_File) as fp: Simulation_Data[Case]["Cell_Fates"] = json.load(fp)
        Simulation_Data[Case]["Cell_Fate_File"] = Cell_Fate_File
        Modelfile = os.path.join(Parent_Dir, Patient_Id + "_" + Case,
                             "Model_Data_%s_%s.pickle" % (Patient_Id, Case))
        with open(Modelfile) as fp: Simulation_Data[Case]["Model_Data"] = pickle.load(fp)
        Simulation_Data[Case]["Modelfile"] = Modelfile


    print("Diagnostic output for case %s" % index)
    Sweepdata_Control = Simulation_Data["Control"]["Sweepdata"]
    Sweepdata_Dox = Simulation_Data["Dox"]["Sweepdata"]
    Booldata_Control = Simulation_Data["Control"]["Model_Data"]
    Booldata_Dox = Simulation_Data["Dox"]["Model_Data"]
    for Case in Simulation_Data:
        with open("../../tests/p53_Boolean_%s_%s.json" % (Patient_Id, Case)) as fp: Network = json.load(fp)
        Indicators = Convert_Indicator(Network["cell_states"])
        Cell_Fate_Total, Cell_Fate_Probabilities = Cell_Fate(Simulation_Data[Case]["Model_Data"], Network["indicator"])
        cell_fate_sweep = [elem["choibool"]["data"] for elem in Simulation_Data[Case]["Model_Data"].values() ]
        Cell_Fate_Total_Lookup, Cell_Fate_Probabilities_Lookup = Cell_Fate_Lookup(cell_fate_sweep, Indicators, Network["indicator_nodes"])
        Simulation_Data[Case]["Cell_Fate_Probabilities"] = Cell_Fate_Probabilities
        Simulation_Data[Case]["Cell_Fate_Probabilities_Lookup"] = Cell_Fate_Probabilities_Lookup
    if 0:
        Print_Sweeps()


        Write_Nodes(indices)
        Write_Diffs(indices)


