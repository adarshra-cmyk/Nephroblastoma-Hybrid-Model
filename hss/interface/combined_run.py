#!/usr/bin/env python

import os, sys, json
import pickle, copy
import itertools, random
import multiprocessing as mp
from optparse import OptionParser

script_dirs = ["solver", "interface", "visualization", "utils", "../tests"]

for dirs in script_dirs:
    sys.path.append(os.path.abspath("../%s" % dirs))

import odesolve, boolsolve, sweep
import Dummy_Functions
#from visualize import PlotSweepOde, PlotSweepBool


def Solve(solver, reinitialize=False, updatemodel = True):
    """
    This is the general function that runs the appropriate
    methods of a solver
    """
    if reinitialize:
        solver.Readfile()
        solver.Initialize_Data()
    solver.Createtempfile()
    solver.Change_Parameters()
    solver.Writefile()
    solver.Solve()
    solver.Get_Data()
    if updatemodel:
        solver.Readfile(filename = solver.tmpfile)
    solver.Cleanup()

def Interface(model, interface):

    start, end = model.data_indices[-1]
    for key,value in model.data.items():
        for ii, elem in enumerate(interface):
            for node, comp in elem["nodes"]:
                if node in key:
                    interface[ii]["nodes"][(node, comp)] = value[start:end]
                    break

def Discretize(data, upper = 0.67, lower = 0.33):
    """
    Function that converts continuous concentration to
    discrete
    """
    discrete_data = {}

    for ii, elem in enumerate(data):
        for key, value in elem["nodes"].items():
            node, comp = key
            steady_state = value[-1]
            peak_conc = max(value)
            if steady_state > upper*peak_conc:
                discrete_data[node] = 1
            elif steady_state < lower*peak_conc:
                discrete_data[node] = 0
            else:
                if random.choice([0,1]):
                    discrete_data[node] = 1
            
    return discrete_data

def Continuous(interface, Peak_Conc, upper = 0.67, lower = 0.33):
    """
    Converts the discrete status of nodes into continuous
    values based on the peak concentrations
    """
    continuous_data = {}
    for ii, elem in enumerate(interface):
        for key, value in elem["nodes"].items():
            if elem["type"] == "boolean":
                continuous_data[key] = Peak_Conc[key]*(upper*value + lower*(1 - value))

    return continuous_data

def Coupled_Run(model_instances, reinitialize = False, updatemodel = True):
    """
    This runs a single iteration of a combination of models
    in the specified order
    """

    Peak_Conc = {}
    continuous_data = {}
    discrete_data = {}
    Interface_Data = { key : Run_Info["models"][key]["interfaces"] for key in Run_Info["model_runs"] }
    for key, value in Interface_Data.items():
        for ii, elem in enumerate(value):
            Interface_Data[key][ii]["nodes"] = dict(zip(map(tuple,elem["nodes"]), [0]*len(elem["nodes"])))

    for name, model in zip(Run_Info["model_runs"], model_instances):
        if model["type"] == "ode":
            Solve(model["instance"], reinitialize = reinitialize, updatemodel = updatemodel)
            if reinitialize and updatemodel:
                model["instance"].parameter = []
            Interface(model["instance"], Interface_Data[name])
            #print "ODE Output: ", ','.join(["%s = [%s,%s]" % (key, value[0], value[-1]) for key, value in Interface_Data[0].items()])
            for elem in Interface_Data[name]:
                Peak_Conc.update({ key : max(value) for key, value in elem["nodes"].items() })
            if not reinitialize:
                continuous_data = Continuous(Interface_Data[Interface_Data[name][0]["other"]], Peak_Conc)
            model["instance"].interface_parameter = []
            compartments = { key : value for key, value in model["interfaces"][0]["nodes"] }
            for key, value in continuous_data.items():
                interface_data = {
                    "Paramtype" : "Initial Species Values",
                    "substitute" : {
                        "compartment" : compartments[key[0]],
                        "species" : key[0]
                        },
                    "value" : value
                    }
                model["instance"].interface_parameter.append(interface_data)
        if model["type"] == "boolean":
            discrete_data = Discretize(Interface_Data[Interface_Data[name][0]["other"]])
            if reinitialize and (not updatemodel):
                model["instance"].parameter["states"].update(discrete_data)
            else:
                model["instance"].parameter["states"] = discrete_data
            Solve(model["instance"], reinitialize = reinitialize, updatemodel = False)
            Interface(model["instance"], Interface_Data[name])
            #print "Boolean Output: ", ','.join(["%s = %s" % (key, value) for key, value in Interface_Data.items()])

def Cell_Fate(boolrun, indicators, default_state = None):
    """
    This function gets the final state of the
    boolean and compares the status of specific
    nodes with that in indicator to identify the
    final state
    """
    final_state = boolrun.states
    for key, value in indicators.items():
        if all( final_state[k] == v for k, v in value.items() ):
            cell_fate = key
            break
    else:
        cell_fate = default_state

    return cell_fate 

def Coupled_Loop(args):
    """
    Runs the inner loop for batch run
    """
    num, Unconstrained_Nodes, init_state, sweep_elem, updatemodel = args
    model_data = {}
    cell_fate = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }

    model_instance = []
    for mod_run in Run_Info["model_runs"]:
        model = copy.deepcopy(Run_Info["models"][mod_run])
        if model["type"] == "ode":
            oderun = odesolve.OdeSolver(model["file"], sweep_elem, conv = model["conv"])
            oderun.parameter.extend(model["initialize"])
            model["instance"] = oderun
            model_instance.append(model)
        if model["type"] == "boolean":
            with open(model["file"]) as fp: boolmodel = json.load(fp)
            boolmodel["changes"]["states"] = dict(zip(Unconstrained_Nodes, init_state))
            boolrun = boolsolve.BoolNetSolver(model["file"], boolmodel["changes"])
            model["instance"] = boolrun
            model_instance.append(model)


    Coupled_Run(model_instance, reinitialize = True, updatemodel = updatemodel)

    for step in range(Run_Info["steps"]):
        Coupled_Run(model_instance, reinitialize = False, updatemodel = updatemodel)

        if step % 1 == 0:
            with open("Sim_Data%d.pickle" % step, "wb") as fp: pickle.dump(
                    {"odedata" : oderun.data,
                     "booldata" : boolrun.data,
                     "odemodel" : oderun.xmlstring,
                     "boolmodel" : boolrun.network,
                     "rules" : boolrun.Rules
                    }, fp)
        cell_fate_step = Cell_Fate(boolrun, boolmodel["indicator"], default_state = "cell_senescence")
        cell_fate[cell_fate_step] += 1

    for name, model in zip(Run_Info["model_runs"], model_instance):
        model_data[name] = {}
        model_data[name]["data"] = model["instance"].data
        model_data[name]["parameter"] = model["instance"].parameter
        if model["type"] == "boolean":
            model_data[name]["rules"] = model["instance"].Rules
            model_data[name]["cell_fate"] = cell_fate

    return model_data

def Batch_Build(writefile = ""):
    """
    Create the list of arguments for performing the batch
    run
    """
    arglist = []
    argdict = {}
    Combined_Space = enumerate(itertools.product(Sweep_Space, Memory, init_states))
    for num, loopelem in Combined_Space:
        elem, updatemodel, init_state = loopelem
        arglist.append((num, Unconstrained_Nodes, init_state, elem, updatemodel))
        argdict[num] = (Unconstrained_Nodes, init_state, elem, updatemodel)

    if writefile != "":
        writefile = os.path.splitext(writefile)[0] + ".json"
        with open(writefile, "w") as fp: json.dump(argdict, fp, indent = 4)

    return arglist

def Batch_Run(arglist, Parallel = False):
    """
    Performs a batch run based on specified models and
    running scheme
    """

    if Parallel:
        pool = mp.Pool(min(mp.cpu_count(), len(arglist)))
        #results = pool.map(Coupled_Loop, arglist)
        results = pool.map(Coupled_Loop, arglist)
        pool.close()
        pool.join()
    else:
        results = []
        for args in arglist:
            #results.append(Coupled_Loop(args))
            results.append(Coupled_Loop(args))

    return results

def Batch_Collect(results, writefile = ""):
    """
    Collects the results from a batch run.
    results must be a dictionary with model id as key and the
    data as value
    """
    Cell_Fates = { "cell_death" : [], "cell_growth" : [], "cell_senescence" : [] }
    Cell_Fates_Total = { "cell_death" : 0.0, "cell_growth" : 0.0, "cell_senescence" : 0.0 }
    Modelstates = { key : [] for key in Run_Info["models"].keys() }
    total = 0

    for result in results:
        for key, value in result.items():
            Modelstates[key].append(value)
            if "cell_fate" in value:
                for k, v in value["cell_fate"].items():
                    Cell_Fates[k].append(v)
                    Cell_Fates_Total[k] += v
                    total += v

    Cell_Fate_Probabilities = { key : float(value)/total for key,value in Cell_Fates_Total.items() }

    if writefile != "":
        writefile = os.path.splitext(writefile)[0] + ".json"
        with open(writefile, "w") as fp: json.dump({"Cell_Fates" : Cell_Fates, "Cell_Fate_Probabilities" : Cell_Fate_Probabilities}, fp)

    return Modelstates, Cell_Fate_Probabilities


def Initial_States(Unconstrained_Nodes, limit = 4):
    """
    Function that determines the unconstrained nodes
    and initial states from Boolean models
    """
    initial_state_space = list(itertools.product([0,1], repeat = len(Unconstrained_Nodes)))
    if len(Unconstrained_Nodes) < limit:
        init_states = initial_state_space
    else:
        init_states = [initial_state_space[ii] for ii in random.sample(xrange(0, len(initial_state_space)), 2**(limit - 1))]

    return init_states

def Unconstrained(boolmodel, interfaces):
    """
    This function determines the list of unconstrained nodes
    from a boolean model
    """
    Constrained_Nodes = set(interfaces) | set(boolmodel["changes"]["states"].keys())
    Unconstrained_Nodes = set(boolmodel["network"].keys()) - Constrained_Nodes

    return list(Unconstrained_Nodes)

if __name__ == '__main__':

    usage = "usage: %prog jsonfile"
    parser = OptionParser(usage = usage)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error(usage)
    elif not os.path.isfile(args[0]):
        parser.error("File %s not found" % args[0])
    else:
        with open(args[0]) as fp: Run_Info = json.load(fp)
    
    Dirname = ""
    Local = True # False
    #with open("Run_Info_5XIHQG_Dox_Vincristine.json") as fp: Run_Info = json.load(fp) # _New
    Sweep_Data = Run_Info["sweeps"]["chenode"]
    Sweep_Space = sweep.Generate_Sweeps(Sweep_Data)
    Memory = [True] # , False]

    print Run_Info['run_id']
    #Determine unconstrained nodes
    for key, value in Run_Info["models"].items():
        if value["type"] == "boolean":
            with open(value["file"]) as fp: boolmodel = json.load(fp)
            interfaces = [elem[0] for elem in value["interfaces"][0]["nodes"]]
            Unconstrained_Nodes = Unconstrained(boolmodel, interfaces)
            init_states = Initial_States(Unconstrained_Nodes, limit = 3)
            break

    print 'start batch build'
    arglist = Batch_Build(writefile = os.path.join(Dirname, "Sweepfile_%s.json" % Run_Info["run_id"]))
    #quit()
    if Local:
        print 'start batch run'
        results = Batch_Run(arglist, Parallel = True)
        print 'start batch collect'
        Modelstates, Cell_Fate_Probabilities = Batch_Collect(results, writefile = "Cell_Fates_%s.json" % Run_Info["run_id"])
        print 'save states and fates to file'
        with open("Simulation_Data_%s.pickle" % Run_Info['run_id'], "wb") as fp: pickle.dump({"Modelstates" : Modelstates, "Cell_Fates" : Cell_Fate_Probabilities}, fp)
    
