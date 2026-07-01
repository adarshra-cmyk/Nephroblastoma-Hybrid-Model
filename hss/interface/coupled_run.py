#!/usr/bin/env python

import os, sys, json
import pickle
import itertools, random
from multiprocessing import Pool

sys.path.append(os.path.join(os.path.expanduser('~'), "Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/interface/"))
sys.path.append(os.path.join(os.path.expanduser('~'), "Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/solver/"))
sys.path.append(os.path.join(os.path.expanduser('~'), "Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/visualization/"))
sys.path.append(os.path.join(os.path.expanduser('~'), "Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/utils/"))

from odesolve import OdeSolver
from boolsolve import BoolNetSolver
from random import choice
from sweep import Generate_Sweeps
from osutils import Make_Directory
from visualize import PlotSweepOde, PlotSweepBool

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

def Interface(solver, interface):

    Interface_Data = {}
    start, end = solver.data_indices[-1]
    for key,value in solver.data.items():
        for elem in interface.keys():
            if elem in key:
                Interface_Data[elem] = value[start:end]
                break

    return Interface_Data

def Discretize(continuous_data):
    """
    Runs a combination of models based on a
    provided scheme consisting of interface
    information, sequence and time steps
    """
    discrete_data = {}

    for key, value in continuous_data.items():
        steady_state = value[-1]
        peak_conc = max(value)
        if steady_state > 0.6*peak_conc:
            discrete_data[key] = 1
        elif steady_state < 0.33*peak_conc:
            discrete_data[key] = 0
        else:
            if choice([0,1]):
                discrete_data[key] = 1

    return discrete_data

def Continuous(discrete_data, Peak_Conc):
    """
    Converts the discrete status of nodes into
    continuous values based on the peak concentrations
    """
    continuous_data = {}
    for key, value in discrete_data.items():
        continuous_data[key] = Peak_Conc[key]*(0.6 * value + 0.33 * (1 - value))

    return continuous_data

def Coupled_Run(oderun, boolrun, interface, reinitialize = False, updatemodel = True):
    """
    Runs the ODE and boolean models in a coupled
    fashion
    """
    Peak_Conc = {}
    Solve(oderun, reinitialize = reinitialize, updatemodel = updatemodel)
    if reinitialize and updatemodel:
        oderun.parameter = []
    Interface_Data = Interface(oderun, interface)
    print "ODE Output: ", ','.join(["%s = [%s,%s]" % (key, value[0], value[-1]) for key, value in Interface_Data.items()])
    Peak_Conc.update({ key : max(value) for key, value in Interface_Data.items() })
    discrete_data = Discretize(Interface_Data)

    if reinitialize or (not updatemodel):
        boolrun.parameter["states"].update(discrete_data)
    else:
        boolrun.parameter["states"] = discrete_data
    Solve(boolrun, reinitialize = reinitialize, updatemodel = False)
    Interface_Data = Interface(boolrun, interface)
    print "Boolean Output: ", ','.join(["%s = %s" % (key, value) for key, value in Interface_Data.items()])
    continuous_data = Continuous(discrete_data, Peak_Conc)
    oderun.interface_parameter = []
    for key, value in continuous_data.items():
        oderun.interface_parameter.append({ "Paramtype" : "Initial Species Values",
                                  "substitute" : {"compartment" : interface[key],"species" : key},
                                  "value" : value
                                  })
                                  
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

def Batch_Run_Ode():
    """
    Performs a batch run for a single ode module
    """
    oderuns = []
    for elem in Sweep_Space:
        oderun = OdeSolver(Run_Info["odefile"], elem, conv = conv)
        oderun.parameter.extend(Ode_Initialize.values())
        Solve(oderun, reinitialize = True, updatemodel = False)
        oderuns.append(oderun)

    return oderuns

def Batch_Run_Bool(modify_rules = False):
    """
    Performs batch run of a single boolean module
    """
    Cell_Fates = []
    boolruns = []
    for elem in Sweep_Space:
        boolrun = BoolNetSolver(Run_Info["boolfile"], boolmodel["changes"])
        if modify_rules:
            boolrun.Readfile()
            boolrun.Initialize_Data(Writefile="yes")
            Rulefile = raw_input("Modify the filename and provide the name: ")
            boolrun.Initialize_Data(Rulefile = Rulefile)
            for _ in range(steps):
                boolrun.Createtempfile()
                boolrun.Change_Parameters()
                boolrun.Writefile()
                boolrun.Solve()
                boolrun.Get_Data()
                boolrun.Cleanup()
        else:
            Solve(boolrun, reinitialize = True, updatemodel = False)
            for _ in range(steps):
                Solve(boolrun, reinitialize = False, updatemodel = False)
        cell_fate = Cell_Fate(boolrun, boolmodel["indicator"], default_state = "cell_senescence")
        Cell_Fates.append(cell_fate)
        boolruns.append(boolrun)

    return boolruns, Cell_Fate


def Coupled_Loop(args):
    """
    Runs the inner part of loop for batch run
    """
    num, Unconstrained_Nodes, init_state, sweep_elem, updatemodel = args
    odedata = {}
    booldata = {}
    cell_fate = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    boolmodel["changes"]["states"] = dict(zip(Unconstrained_Nodes, init_state))
    print "Initial State %s, Sweep element %s, updatemodel = %s" % (str(boolmodel["changes"]["states"]), str(sweep_elem), str(updatemodel))
    start_time = time.time()
    oderun = OdeSolver(Run_Info["odefile"], sweep_elem, conv = conv)
    oderun.parameter.extend(Ode_Initialize.values())
    boolrun = BoolNetSolver(Run_Info["boolfile"], boolmodel["changes"])
    Coupled_Run(oderun, boolrun, interface, reinitialize = True, updatemodel = updatemodel)
    print "Initial run completed in %3.2f min for num = %d" % ((time.time() - start_time)/60, num)
    for step in range(steps):
        start_time = time.time()
        Coupled_Run(oderun, boolrun, interface, reinitialize = False, updatemodel = updatemodel)
        if step == 0 or (step + 1) % 5 == 0:
            print "Step %d completed in %3.2f min for num = %d" % (step, (time.time() - start_time)/60, num)
            with open(os.path.join(Dirname, "Sim_Data%d.pickle" % num), "wb") as fp: pickle.dump({"odedata" : oderun.data, "booldata" : boolrun.data, "odemodel" : oderun.xmlstring, "boolmodel" : boolrun.network, "rules" : boolrun.Rules}, fp)
            cell_fate[Cell_Fate(boolrun, boolmodel["indicator"], default_state = "cell_senescence")] += 1
    #oderuns.append(oderun)
    #boolruns.append(boolrun)
    odedata["data"] = oderun.data
    odedata["parameter"] = oderun.parameter
    booldata["data"] = boolrun.data
    booldata["parameter"] = boolrun.parameter
    booldata["rules"] = boolrun.Rules
    booldata["cell_fate"] = cell_fate


    return odedata, booldata

def Batch_Run(Parallel = False):
    """
    Performs a batch run by initializing appropriate
    variation of instances of different solvers, running
    and calculating cell fates.
    """
    Cell_Fates = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    total = 0
    oderuns = []
    boolruns = []
    arglist = []
    argdict = {}
    Odestates = []
    Boolstates = []
    Constrained_Nodes = set(interface.keys()) | set(boolmodel["changes"]["states"].keys())
    Unconstrained_Nodes = set(boolmodel["network"].keys()) - Constrained_Nodes
    Unconstrained_Nodes = list(Unconstrained_Nodes)
    initial_state_space = list(itertools.product([0,1], repeat = len(Unconstrained_Nodes)))

    Make_Directory(os.path.join(os.getenv("PWD"), Dirname))

    if len(Unconstrained_Nodes) < 4:
        init_states = initial_state_space
    else:
        init_states = [initial_state_space[ii] for ii in random.sample(xrange(0, len(initial_state_space)), 8)]
    #reinitialize = False
    #init_states = initial_state_space[:4]
    if Parallel:
        for num, loopelem in enumerate(itertools.product(Sweep_Space, [True, False], init_states)):
            elem, updatemodel, init_state = loopelem
            arglist.append((num, Unconstrained_Nodes, init_state, elem, updatemodel))
            argdict[num] = (Unconstrained_Nodes, init_state, elem, updatemodel)
        with open(os.path.join(Dirname, "Data_Id.json"), "w") as fp: json.dump(argdict, fp, indent = 4)
        pool = Pool(16)
        results = pool.map(Coupled_Loop, arglist)
        pool.close()
        pool.join()
        for odedata, booldata in results:
            Odestates.append(odedata)
            Boolstates.append(booldata)
            for key, value in booldata["cell_fate"].items():
                Cell_Fates[key] += value
                total += value

    else:
            
        for num, loopelem in enumerate(itertools.product(Sweep_Space[:1], [True], init_states)):
            elem, updatemodel, init_state = loopelem
            arglist.append((num, Unconstrained_Nodes, init_state, elem, updatemodel))
            argdict[num] = (Unconstrained_Nodes, init_state, elem, updatemodel)
            args = num, Unconstrained_Nodes, init_state, elem, updatemodel
            odedata, booldata = Coupled_Loop(args)
            Odestates.append(odedata)
            Boolstates.append(booldata)
            for key, value in booldata["cell_fate"].items():
                Cell_Fates[key] += value
                total += value
    Cell_Fate_Probabilities = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    for key,value in Cell_Fates.items():
        Cell_Fate_Probabilities[key] = float(value)/total

    for key, value in Cell_Fate_Probabilities.items():
        print "%s = %d, %4.3f" % (key, Cell_Fates[key], value)

    with open("Cell_Fates_%s.json" % sweep_id, "w") as fp: json.dump(Cell_Fate_Probabilities, fp)

    return Odestates, Boolstates, Cell_Fate_Probabilities

def Odeplots(oderuns, plot_parameters, sweep_id):

    ps = PlotSweepOde(sweep_id, oderuns, plot_parameters, oderuns[0])
    ps.get_data()

    for elem in plot_parameters:
        fig = ps.timecourse(elem, end_time = "end")
        ps.store_figstr(fig, "timecourse", elem, end_time = "end")
        ps.save_fig(fig, "timecourse", elem, end_time = "end")
        ps.close_fig(fig)

    ps.save_figstr()

def Boolplots(boolruns, plot_parameters, sweep_id):

    ps = PlotSweepBool(sweep_id, boolruns, plot_parameters)
    ps.get_data()
    tables = []
        
    for elem in plot_parameters:
        fig = ps.statusplots(elem)
        ps.store_figstr(fig, elem)
        ps.save_fig(fig, elem)
        ps.close_fig(fig)
    tabletext = ps.statustable()

    with open("tables.csv","w") as fp: fp.write(tabletext)
        

if __name__ == '__main__':

    #Initialize Models
    #conv = 602214179000000
    #inputfile = "../../tests/ErbB4-JAK2-STAT5_Yamda_Combined_Exec.cps"
    #networkfile = "../../tests/ErbB4_Boolean.json"
    #interfacefile = "Interface_ErbB4.json"
    with open("Run_Info.json") as fp: Run_Info = json.load(fp)
    Dirname = "Temp_Data%s" % sweep_id.replace(' ', '_')
    Run_Mode = "Coupled"
    sweep_id = Run_Info["sweep_id"]
    steps = Run_Info["steps"]

    with open(Run_Info["sweepfile"]) as fp: Sweep_Data = json.load(fp)
    with open(Run_Info["odeinitialize"]) as fp: Ode_Initialize = json.load(fp)
    Sweep_Space = Generate_Sweeps(Sweep_Data)
    with open(Run_Info["boolfile"]) as fp: boolmodel = json.load(fp)
    with open(Run_Info["interfacefile"]) as fp: interface = json.load(fp)


    if Run_Mode == "Ode":
        oderuns = Batch_Run_Ode()
    if Run_Mode == "Boolean":
        boolruns, Cell_Fates = Batch_Run_Bool()
    else:
        Odestates, Boolstates, Cell_Fate_Probabilities = Batch_Run(Parallel = True)
        with open("Simulation_Data_%s.pickle" % sweep_id, "wb") as fp: pickle.dump({ "Odestates" : Odestates, "Boolstates" : Boolstates }, fp)
    Odedata = []
    Booldata = []

    if Run_Mode == "Ode":
        for oderun in oderuns:
            data = {}
            data["data"] = oderun.data
            data["parameter"] = oderun.parameter
            Odedata.append(data)

    if Run_Mode == "Boolean":
        for boolrun in boolruns:
            data = {}
            data["data"] = boolrun.data
            data["parameter"] = boolrun.parameter
            Booldata.append(data)


    if Run_Info["Plots"]:
        if Run_Mode == "Ode" or Run_Mode == "Coupled":
            Odeplots(Odedata, Run_Info["plot_parameters_ode"], sweep_id)
        if Run_Mode == "Boolean" or Run_Mode == "Coupled":
            Boolplots(Booldata, Run_Info["plot_parameters_bool"], sweep_id)
    #States = boolruns[0].Attractor_Analysis(Random = True, N = 50000, Outfile = "p53_Attractors")
