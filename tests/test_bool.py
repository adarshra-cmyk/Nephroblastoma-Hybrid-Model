#!/usr/bin/env python

# Script to test the runs for different cases
from __future__ import print_function
import sys
import json, copy, pickle
from pprint import pprint

from hss.interface import hybrid_run
#import hybrid_run
import test_runs

def Cell_Fate(results, state_key = "cell_fate"):
    """
    Calculates the cell fates based on a given set
    of results
    """
    Cell_Fates = { "cell_death" : [], "cell_growth" : [], "cell_senescence" : [] }
    Cell_Fates_Total = { "cell_death" : 0.0, "cell_growth" : 0.0, "cell_senescence" : 0.0 }
    total = 0.0
    for result in results:
        for key, value in result.items():
            if key == state_key:
                for k, v in value.items():
                    Cell_Fates[k].append(v)
                    Cell_Fates_Total[k] += v
                    total += v

    Cell_Fate_Probabilities = { key : float(value)/total for key,value in Cell_Fates_Total.items() }

    return Cell_Fates_Total, Cell_Fate_Probabilities

def Cell_Fate_Simulation(boolrun, indicators, Target_Nodes):
    """
    Calculates the cell fate per simulation step
    """
    final_states = boolrun.states
    state_key = []
    for node in Target_Nodes:
        state_key.extend([node, final_states[node]])
    cell_fate = indicators[tuple(state_key)]

    return cell_fate

def Run_Bool(boolrun, initial_run = False, steps = 20, updatemodel = False):
    """
    Runs a particular instance of a boolean model
    """
    if initial_run:
        boolrun.Readfile()
        boolrun.Initialize_Data()
        boolrun.Change_Parameters()
        boolrun.Initialize_Data()
    else:
        if not updatemodel:
            boolrun.Change_Parameters()
            boolrun.Initialize_Data(Lose_Memory = True)
        
    boolrun.Createtempfile()
    boolrun.Writefile()
    boolrun.Solve(steps = steps)
    boolrun.Get_Data()
    boolrun.Cleanup()

def Display_Bool(boolrun, boolmodel):

    Nodes = ["CDK1", "PTEN", "ATM", "TP53", "MDM2"]
    CNodes = ["CDK2","CASP9"]
    INodes = ["ERK_PP","AKT_P","Raf_P","PTEN"]
    cell_fate_step = hybrid_run.Cell_Fate(boolrun, boolmodel["indicator"], default_state = "cell_senescence")

    print("Drug Nodes:")
    print([(key, boolrun.data[key]) for key in Nodes])
    print("Cell Fate Nodes:")
    print([(key, boolrun.data[key]) for key in CNodes])
    print("Interface Nodes:")
    print([(key, boolrun.data[key]) for key in INodes])
    print("Cell Fate = ", cell_fate_step)

def Sweep_Bool(Sweep_No, boolmodel):
    """
    Runs the boolean model over a particular
    sweep elements
    """
    cell_fate = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    cell_fate_lookup = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    args = Sweepdata[Sweep_No]["args"]
    num, Unconstrained_Nodes, init_state, sweep_elem, updatemodel = args

    model_data = {}
    boolmodel["changes"]["states"] = dict(zip(Unconstrained_Nodes, init_state))
    boolrun = hybrid_run.boolsolve.BoolNetSolver(model["modfile"], boolmodel["changes"])


    Run_Bool(boolrun, initial_run = True, steps = 1, updatemodel = updatemodel)
    for step in range(Steps):
        Run_Bool(boolrun, steps = 1)
        cell_fate_step = hybrid_run.Cell_Fate(boolrun, boolmodel["indicator"], default_state = "cell_senescence")
        cell_fate[cell_fate_step] += 1
        cell_fate_step_lookup = Cell_Fate_Simulation(boolrun, Indicators["G1toS"], boolmodel["indicator_nodes"]["G1toS"])
        #Additional processing for vincristine
        if cell_fate_step_lookup != "cell_death" and "Vincristine" in druglist:
            Run_Bool(boolrun, steps = 1)
            cell_fate_step_lookup = Cell_Fate_Simulation(boolrun, Indicators["G2toM"], boolmodel["indicator_nodes"]["G2toM"])
            
        cell_fate_lookup[cell_fate_step_lookup] += 1

    model_data["data"] = boolrun.data
    model_data["cell_fate"] = cell_fate
    model_data["cell_fate_lookup"] = cell_fate_lookup

    return model_data, boolrun


if __name__ == '__main__':

    Steps = 20
    Usage = "python test_bool Patient_ID Case"
    if len(sys.argv) != 3:
        raise Exception(Usage)
    Patient_ID = sys.argv[1]
    Case = sys.argv[2]
    Sweep_No = "24"
    Model_File = "Run_Info_%(id)s_%(case)s.json" % { "id" : Patient_ID, "case" : Case }
    Logfile = "Boolrun_%(id)s_%(case)s.log" % { "id" : Patient_ID, "case" : Case }
    druglist = Case.split("_")
    Indicators = {}

    with open(Model_File) as fp: Run_Info = json.load(fp)

    #Sweepfile = "Temp_Data/%(id)s_%(case)s/Sweepfile_%(id)s_%(case)s.json" % { "id" : Patient_ID, "case" : Case }
    Sweepfile = "Sweepfile_%(id)s_%(case)s.json" % { "id" : Patient_ID, "case" : Case }
    with open(Sweepfile) as fp: Sweepdata = json.load(fp)
    model = copy.deepcopy(Run_Info["models"]["choibool"])
    with open(model["modfile"]) as fp: boolmodel = json.load(fp)

    for key in boolmodel["indicator_nodes"]:
        Indicators[key] = test_runs.Convert_Indicator(boolmodel["cell_states"][key])

    results = []
    model_ensemble = []
    stdout_orig = sys.stdout

    try:
        with open(Logfile,"w") as fp:
            sys.stdout = fp
            for Sweep_Elem in Sweepdata:
                model_data, boolrun = Sweep_Bool(Sweep_Elem, boolmodel)
                results.append(model_data)
                model_ensemble.append(boolrun)
            with open("Datafile_%(id)s_%(case)s.json" % { "id" : Patient_ID, "case" : Case }, "w") as dfp: json.dump(results, dfp)
            #with open("Modelfile_%(id)s_%(case)s.pickle" % { "id" : Patient_ID, "case" : Case }, "w") as dfp: pickle.dump({"ensemble" : model_ensemble}, dfp)
            CFP_Simulation,CFP_Simulation_Probability = Cell_Fate(results)
            CFP_Simulation_Lookup,CFP_Simulation_Probability_Lookup = Cell_Fate(results, state_key = "cell_fate_lookup")
            cell_fate_sweep = [elem["data"] for elem in results]
            #CFP_Post, CFP_Post_Probability = test_runs.Cell_Fate(cell_fate_sweep, boolmodel["indicator"])
            CFP_Post_Lookup, CFP_Post_Probability_Lookup = test_runs.Cell_Fate_Lookup(cell_fate_sweep, Indicators["G1toS"], boolmodel["indicator_nodes"]["G1toS"])
            print("Cell Fate numbers and probability from simulation")
            print("old")
            pprint(CFP_Simulation)
            pprint(CFP_Simulation_Probability)
            print("lookup")
            pprint(CFP_Simulation_Lookup)
            pprint(CFP_Simulation_Probability_Lookup)

            print("Cell Fate numbers and probability after post processing")
            print("old")
            pprint(CFP_Post)
            pprint(CFP_Post_Probability)
            print("lookup")
            pprint(CFP_Post_Lookup)
            pprint(CFP_Post_Probability_Lookup)
    except Exception:
        raise
    finally:
        sys.stdout = stdout_orig
