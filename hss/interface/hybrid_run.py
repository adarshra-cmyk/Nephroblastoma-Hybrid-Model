#!/usr/bin/env python

"""
This script contains the functions to couple different
continuous and discrete modes using interface information
defined with the model. Using different command line flags
this script can be run either to run the models individually
or together.

Example Run
-----------
This script is typically invoked from other batch setup scripts.
However it can also be run standalone for testing purposes like
below

    $ python hybrid_run.py Arguments_5XIHQG_Control_24.json Run_Info_5XIHQG_Control.json

In the above the first argument is a json file that contains the
list of arguments and the second file contains run specific
information for the particular patient and drug combination.

Input Files
-----------
The two main files needed for the script are

- `Arguments_<sweep-id>_<num>.json` This is the file containing
a list of arguments to be supplied to the function `Coupled_Run`.
- `Run_Info_<sweep-id>.json` This is the json file containing the
information about individual models, interfaces and location of
other files.

Output Data
-----------
- `Model_Run_<sweep-id>.pickle` This is the main pickle file
containing all the data for the specific sweep elements including
the time course data, boolean node status and cell fates.

"""

import os, sys, json
import pickle, copy
import itertools, random
import multiprocessing as mp

script_dirs = ["solver", "interface", "visualization", "utils", "../tests"]

for dirs in script_dirs:
    sys.path.append(os.path.abspath("../%s" % dirs))

from hss.solver import odesolve, boolsolve, sweep
import Dummy_Functions
#from visualize import PlotSweepOde, PlotSweepBool

def Run_Bool(boolrun, initial_run = False, steps = 20, updatemodel = False):
    """
    Runs an instance of the `BoolNetSolver` class for particular
    number of steps and update information

    Parameters
    ----------
    - `boolrun` : `boolsolve.BoolNetSolver` This is an instance
    of the Boolean model to be solved.
    - `initial_run` : `bool` A flag specifying if the Boolean model
    is to be run for the first time.
    - `steps` : `int` The number of step fror which the boolean
    model is to be run.
    - `updatemodel` : `bool` A flag indicating whether the model
    will update its initial state using the values from the last
    step or not.
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


def Convert_Indicator(indicator):
    """
    Converts the indicator into a form keyed by different
    cell fates

    Parameters
    ----------
    - `indicator` : `list` A nested list of indicator states.

    Returns
    -------
    `dict` A dictionary containing the indicator states which
    have the different cell fates as keys.
    """
    Indicators = {}
    for elem in indicator:
        key = tuple(elem for sublist in elem[0].items() for elem in sublist)
        Indicators[key] = elem[1]

    return Indicators


def Solve(solver, reinitialize=False, updatemodel = True):
    """
    This is the general function that runs the appropriate
    methods of a `solver` instance of the `SystemSolver` class
    (or a class that derives from it).

    Parameters
    ----------
    - `solver` : `system_solver.SystemSolver` An instance of the `Systemsolver` class or another class that inherits from it.
    - `reinitialize` : `bool` A flag that specifies whether or not
    to reinitialize the model to its starting configuration
    - `updatemodel` : `bool` A flag that indicates whether or not to
    use the present model state as the initial state of the next step.
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


def Interface(model, name, Interface_Data):
    """
    This updates the discrete or continuous state of the interface
    nodes of the boolean or ode model respectively using the
    interface information from the previous step

    Parameters
    ----------
    - `model` : `system_solver.SystemSolver` An instance of the `SystemSolver` class or any other class derived from it.
    - `name` : `str` Name of the particular ode or boolean model
    - `Interface_Data` : `dict` A dictionary containing the interface
    information.

    Returns
    -------
    `dict` A dictionary containing the modified interface information.
    """

    Temp_Interface_Data = copy.deepcopy(Interface_Data)
    start, end = model.data_indices[-1]
    for key,value in model.data.items():
        for ii, elem in enumerate(Temp_Interface_Data[name]):
            for node, comp in elem["nodes"]:
                if node == key.split("-")[0]:
                    Temp_Interface_Data[name][ii]["nodes"][(node, comp)] = value[start:end]
                if node == "AKT_P" and key.split("-")[0] == "AKT_P_P":
                    Temp_Interface_Data[name][ii]["nodes"][(node, comp)] = value[start:end]

    return Temp_Interface_Data


def Discretize(data, upper = 0.67, lower = 0.33):
    """
    Function that converts continuous concentration to
    discrete

    Parameters
    ----------
    - `data` : `dict` Data from ODE (continuous).
    - `upper` : `float` A fraction that is used to set the upper
    threshold by multiplying it with the peak concentration.
    - `lower` : `float` A fraction that is used to set the lower
    threshold by multiplying it with the peak concentration.

    Returns
    -------
    `dict` The discretized data with the same keys as the input
    continuous data.
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


def Continuous(interface, Peak_Conc, Steady_State, upper = 0.67, lower = 0.33):
    """
    Converts the discrete status of nodes into continuous
    values based on the peak concentrations

    Parameters
    ----------
    - `interface` : `dict` The interface data from the last step.
    - `Peak_Conc` : `float` The peak concentrations of the interface nodes from the last step.
    - `Steady_State` : `float` The steady state concentration of the interface nodes from the last step.
    - `upper` : `float` A fraction that is used to set the upper
    threshold by multiplying it with the peak concentration.
    - `lower` : `float` A fraction that is used to set the lower
    threshold by multiplying it with the peak concentration.

    Returns
    -------
    `dict` The continuous form of the discrete interface concentrations.
    """
    continuous_data = {}
    for ii, elem in enumerate(interface):
        for key, value in elem["nodes"].items():
            if elem["type"] == "boolean":
                if value[-1]:
                    continuous_data[key] = Steady_State[key] if Steady_State[key] > Peak_Conc[key]*upper else Peak_Conc[key]*upper
                else:
                    continuous_data[key] = Steady_State[key] if Steady_State[key] < Peak_Conc[key]*lower else Peak_Conc[key]*lower

    return continuous_data


def Odesolve(name, model, Interface_Data, reinitialize, updatemodel, coupled = True):
    """
    This function runs the appropriate methods for the ODE solver
    and changes the model and interface data by getting the peak
    concentrations.
    """
    #Copy made to ensure that function doesn't change the interface data
    Temp_Interface_Data = copy.deepcopy(Interface_Data)
    continuous_data = {}
    Peak_Conc = {}
    Steady_State = {}
    compartments = { key : value for key, value in model["interfaces"][0]["nodes"] }
    if reinitialize:
        model["instance"].Readfile()
        model["instance"].Initialize_Data()
    model["instance"].Createtempfile()
    model["instance"].Change_Parameters()
    model["instance"].Writefile()
    model["instance"].Solve()
    model["instance"].Get_Data()
    start, end = model["instance"].initial_indices
    if updatemodel:
        model["instance"].Readfile(filename = model["instance"].tmpfile)
    model["instance"].Cleanup()
    if reinitialize and updatemodel:
        model["instance"].parameter = []
    Temp_Interface_Data = Interface(model["instance"], name, Temp_Interface_Data)
    for species, conc in model["instance"].data.items():
        for node, comp in Temp_Interface_Data[name][0]["nodes"]:
            if node == species.split("-")[0]:
                Peak_Conc[(node, comp)] = max(conc[start:end])
            if node == "AKT_P" and species.split("-")[0] == "AKT_P_P":
                Peak_Conc[(node, comp)] = max(conc[start:end])
    for elem in Temp_Interface_Data[name]:
        Steady_State.update({ key : value[-1] for key, value in elem["nodes"].items() })
    if not reinitialize:
        continuous_data = Continuous(Temp_Interface_Data[Temp_Interface_Data[name][0]["other"]], Peak_Conc, Steady_State)
    if coupled:
        model["instance"].interface_parameter = []
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

    return Temp_Interface_Data


def Boolsolve(name, model, Interface_Data, reinitialize, updatemodel, atm_activation_state = 0, coupled = True):
    """
    This function runs the boolean model for a single time
    step. Before running the boolean solver it gets the discrete node
    states and uses them to initialize the model.
    """
    #Copy made to ensure that function doesn't change the interface data
    Temp_Interface_Data = copy.deepcopy(Interface_Data)
    discrete_data = {}
    for omodel in Temp_Interface_Data[name]:
        oname = omodel["other"]
        discrete_data.update(Discretize(Temp_Interface_Data[oname]))
    if coupled:
        if reinitialize or (not updatemodel):
            model["instance"].parameter["states"].update(discrete_data)
        else:
            model["instance"].parameter["states"] = discrete_data
    if reinitialize:
        model["instance"].Readfile()
        if atm_activation_state:
            model["instance"].network["ATM"]["base"] = 2
            for node in Run_Info["Radiation"]["nodes"]:
                model["instance"].network[node]["initial_state"] = 1
        model["instance"].Initialize_Data()
        model["instance"].Change_Parameters()
        model["instance"].Initialize_Data()
    else:
        if not updatemodel:
            model["instance"].Change_Parameters()
            model["instance"].Initialize_Data(Lose_Memory = True)
    model["instance"].Createtempfile()
    model["instance"].Writefile()
    model["instance"].Solve()
    model["instance"].Get_Data()
    model["instance"].Cleanup()

    Temp_Interface_Data = Interface(model["instance"], name, Temp_Interface_Data)

    return Temp_Interface_Data


def Coupled_Run(model_instances, models, model_runs, Interface_Data, atm_activation_state = 0, reinitialize = False, updatemodel = True):
    """
    This runs a single iteration of a combination of continuous
    and discrete models in the specified order

    Parameters
    ----------
    - `model_instances` : `list` A list of the model instances which are to be run together.
    - `models` : `list` A list of the model names that are to be run together.
    - `Interface_Data`: `dict` The continuous and discrete concentration of the interface nodes.
    - `atm_activation_state` : `int` A flag indicating whether atm status is activated or not (indicates if radiation is being used or not).
    - `reinitialize` : `bool` A flag indicating whether or not to reset the model to its initial configuration.
    - `updatemodel` : `bool` A flag indicating whether to use the previous model state to initialize the current step or not.

    Returns
    -------
    `dict` A dictionary containing copy of the interface data.
    """

    #Copy made to ensure that function doesn't change the interface data
    Temp_Interface_Data = copy.deepcopy(Interface_Data)
    for name, model in zip(model_runs, model_instances):
        if model["type"] == "ode":
            Temp_Interface_Data = Odesolve(name, model, Temp_Interface_Data, reinitialize, updatemodel)
        if model["type"] == "boolean":
            Temp_Interface_Data = Boolsolve(name, model, Temp_Interface_Data, reinitialize, updatemodel, atm_activation_state = atm_activation_state)

    return Temp_Interface_Data


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


def Cell_Fate_Lookup(boolrun, indicators, Target_Nodes):
    """
    Calculates the cell fate per simulation step using a
    modified data form.
    """
    final_states = boolrun.states
    state_key = []
    for node in Target_Nodes:
        state_key.extend([node, final_states[node]])
    cell_fate = indicators[tuple(state_key)]

    return cell_fate


def Coupled_Loop(args):
    """
    Runs the inner loop for batch run
    """
    num, Unconstrained_Nodes, init_state, sweep_elem, updatemodel, atm_activation_state = args
    reference_drug_list = ['Control', 'Dox', 'Vincristine']
    druglist = [a for a in Run_Info["run_id"].split("_")[1:] if a in reference_drug_list]
    #Steps = Run_Info["steps"] * (3 if updatemodel and "Control" not in druglist else 1)
    Steps = Run_Info["steps"]
    model_data = {}
    cell_fate = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    cell_fate_lookup = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
    Indicators = {}
    step = -1

    model_instance = []
    for modelem in Run_Info["model_runs"]:
        model = copy.deepcopy(Run_Info["models"][modelem])
        if model["type"] == "ode":
            oderun = odesolve.OdeSolver(model["file"], sweep_elem, conv = model["conv"])
            for initelem in model["initialize"]:
                if initelem["substitute"]["species"] != sweep_elem[0]["substitute"]["species"]:
                    oderun.parameter.append(initelem)
            model["instance"] = oderun
            model_instance.append(model)
        if model["type"] == "boolean":
            with open(model["modfile"]) as fp: boolmodel = json.load(fp)
            for key in boolmodel["indicator_nodes"]:
                Indicators[key] = Convert_Indicator(boolmodel["cell_states"][key])

            boolmodel["changes"]["states"] = dict(zip(Unconstrained_Nodes, init_state))
            boolrun = boolsolve.BoolNetSolver(model["modfile"], boolmodel["changes"])
            model["instance"] = boolrun
            model_instance.append(model)

    Interface_Data = { key : values["interfaces"] for key, values in Run_Info["models"].items() }

    for key, value in Interface_Data.items():
        for ii, elem in enumerate(value):
            Interface_Data[key][ii]["nodes"] = dict(zip(map(tuple,elem["nodes"]), [[0]]*len(elem["nodes"])))

    Interface_Data = Coupled_Run(model_instance, Run_Info["models"], Run_Info["model_runs"], Interface_Data, reinitialize = True, updatemodel = updatemodel, atm_activation_state = atm_activation_state)

    for step in range(Steps):
        Coupled_Run(model_instance, Run_Info["models"], Run_Info["model_runs"], Interface_Data, reinitialize = False, updatemodel = updatemodel)

        if step % 20 == 0:
            with open("Sim_Data_%s_%d_%d.pickle" % (Run_Info["run_id"],num,step), "wb") as fp: pickle.dump(
                    {"odedata" : oderun.data,
                     "booldata" : boolrun.data,
                     "odemodel" : oderun.xmlstring,
                     "boolmodel" : boolrun.network,
                     "rules" : boolrun.Rules
                    }, fp)
        boolrun_updated = model_instance[Run_Info["model_runs"].index("choibool")]["instance"]
        cell_fate_step = Cell_Fate(boolrun_updated, boolmodel["indicator"], default_state = "cell_senescence")
        cell_fate[cell_fate_step] += 1
        cell_fate_step_lookup = Cell_Fate_Lookup(boolrun_updated, Indicators["G1toS"], boolmodel["indicator_nodes"]["G1toS"])
        #Additional processing for vincristine
        if cell_fate_step_lookup != "cell_death" and "Vincristine" in druglist:
            #boolean_run = [ key for key, value in Run_Info["models"].items() if value["type"] == "boolean" ]
            #boolean_instance = [ elem for elem in model_instance if elem["type"] == "boolean" ]
            #Coupled_Run(boolean_instance, Run_Info["models"], boolean_run, reinitialize = False, updatemodel = updatemodel)
            #boolrun_updated = boolean_instance[0]["instance"]
            Run_Bool(boolrun_updated, initial_run = False, steps = 1, updatemodel = updatemodel)
            cell_fate_step_lookup = Cell_Fate_Lookup(boolrun_updated, Indicators["G2toM"], boolmodel["indicator_nodes"]["G2toM"])

        cell_fate_lookup[cell_fate_step_lookup] += 1

    for name, model in zip(Run_Info["model_runs"], model_instance):
        model_data[name] = {}
        model_data[name]["data"] = model["instance"].data
        model_data[name]["data_indices"] = model["instance"].data_indices
        model_data[name]["num_data"] = model["instance"].num_data
        model_data[name]["parameter"] = model["instance"].parameter
        if model["type"] == "boolean":
            model_data[name]["rules"] = model["instance"].Rules
            model_data[name]["cell_fate"] = cell_fate
            model_data[name]["cell_fate_lookup"] = cell_fate_lookup
        else:
            model_data[name]["interface_data"] = model["instance"].interface_data

    return model_data


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


if __name__ == '__main__':

    Dirname = ""
    with open(sys.argv[1]) as fp: Args = json.load(fp)
    with open(sys.argv[2]) as fp: Run_Info = json.load(fp)
    model_data = Coupled_Loop(Args["args"])

    with open("Model_Data_%s.pickle" % Args["sweep_id"], "wb") as fp: pickle.dump(model_data, fp)
