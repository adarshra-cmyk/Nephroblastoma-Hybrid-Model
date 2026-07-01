#!/usr/bin/env python

import random, json
from pprint import pprint

def Coupled_Loop(args):
    """
    Dummy function to test the functionality
    of `Batch_Run()`
    """
    num, Unconstrained_Nodes, init_state, sweep_elem, updatemodel = args
    print "In Coupled_Loop arguments num = %d, init_state = %s" % (num, init_state)
    model_data = {}
    model_runs = ["chenode", "choibool"]
    cell_fate = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    fates = cell_fate.keys()
    for step in range(5):
        cell_fate[random.choice(fates)] += 1

    for name in model_runs:
        model_data[name] = {}
        model_data[name]["data"] = [elem + num for elem in range(10)]
        model_data[name]["parameter"] = {"p1" : num, "p2" : 2*num}

        if name == "choibool":
            model_data[name]["rules"] = "Sample rules"
            model_data[name]["cell_fate"] = cell_fate

    return model_data

def Coupled_Run(model_instance, reinitialize = False, updatemodel = True):
    """
    Dummy function to test the functionality of Coupled_Loop()
    """
    Peak_Conc = {}
    discrete_data = {}

    for model in model_instance:
        if model["type"] == "ode":
            print "Solving %s with reinitialize = %s and updatemodel = %s" % (model["type"], reinitialize, updatemodel)
            if reinitialize and updatemodel:
                model["instance"].parameter = []
            model["instance"].data = range(10)
        if model["type"] == "boolean":
            with open(model["file"]) as fp: network = json.load(fp)["network"]
            discrete_data = { key : value["initial_state"] for key, value in network.items() }
            if reinitialize and (not updatemodel):
                model["instance"].parameter["states"].update(discrete_data)
            else:
                model["instance"].parameter["states"] = discrete_data
            print "Current model states", model["instance"].parameter["states"]
            print "Solving %s with reinitialize = %s and updatemodel = %s" % (model["type"], reinitialize, updatemodel)
            model["instance"].data = [1 for _ in range(10)]
            model["instance"].Rules = "Rules"

def Solve(solver, reinitialize = False, updatemodel = True):
    """
    Dummy function to test the functionality of Solver
    function.
    """
    if reinitialize:
        print "Reinitializing by calling Readfile() and Initialize_Data()"

    if updatemodel:
        print "Rereading from solver.tmpfile"

    print "Solution completed"

def print_results(results):
    for elem in results:
        for key, value in elem.items():
            print "Model = %s\n" % key
            pprint(value)
