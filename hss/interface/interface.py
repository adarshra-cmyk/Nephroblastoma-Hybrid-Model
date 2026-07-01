#!/usr/bin/env python

# This script sets up and runs various solver using
# a specified scheme and interface information

from change import Change_Species
from ssolver import OdeRun, OdeData, BoolRun
from random import choice

def Solve(modelfile, changes = [], solver_type = "ode"):
    """
    This performs the initial step of
    running the models and any preprocessing
    step
    """
    Outfile = "Temp_" + modelfile

    if solver_type == "ode":
        if changes != []:
            Change_Species(changes, modelfile, Outfile = Outfile )
        OdeRun(Outfile)
        states = OdeData(Outfile)
    elif solver_type == "boolean":
        with open(modelfile) as fp: network = json.load(fp)
        for key in changes:
            network[key]["initial_state"] = changes[key]
        states = BoolRun(network)
    else:
        raise NotImplementedError("Solver type %s is not implemented" % solver_type)

    return states

def Coupled_Run(Interface, solvers, ode_changes = []):
    """
    Determine a particular running scheme based
    on user provided interface information and
    provided number of steps
    """
    #Initialize
    ode_states = Solve(solvers["ode"]["File"], changes = ode_changes, solver_type = "ode")
    Active_Nodes, Steady_State, Peak_Conc = Discrete(ode_states, Interface["thresh"])
    bool_changes = { key : 1 for key in Active_Nodes }
    bool_states = Solve(solvers["boolean"]["File"], changes = bool_changes, solver_type = "boolean")
    ode_changes = Continuous(bool_states, Peak_Conc, Interface["thresh"], Interface["interface"])

    return ode_states, bool_states, ode_changes, bool_changes
        
def Batch_Run(Interfacefile, Solverfile, steps = 10):
    """
    Runs a batch version of the Coupled_Run steps times
    and collects data for each loop
    """
    Ode_Data = []
    Boolean_Data = []
    with open(Interfacefile) as fp: Interface = json.load(fp)
    with open(Solverfile) as fp: solvers = json.load(fp)

    ode_state, bool_state, ode_changes, bool_changes = Coupled_Run(Interface, solvers)
    Ode_Data.append(ode_state)
    Boolean_Data.append(bool_state)
    
    for ii in range(steps):
        ode_state, bool_state, ode_changes, bool_changes = Coupled_Run(Interface,solvers, ode_changes = ode_changes)
        Ode_Data.append(ode_state)
        Boolean_Data.append(bool_state)

    return Ode_Data, Boolean_Data

def Discrete(continuous_data, thresh):
    """
    Runs a combination of models based on a
    provided scheme consisting of interface
    information, sequence and time steps
    """
    Peak_Conc = {}
    Steady_State = {}
    for key, value in continuous_data.items():
        Peak_Conc[key] = max(value)
        Steady_State[key] = value[-1]

    Active_Nodes = []
    for key in thresh:
        if Steady_State[key] > 0.6*Peak_Conc[key]:
            Active_Nodes.append(key)
        elif Steady_State[key] < 0.33*Peak_Conc[key]:
            pass
        else:
            if choice([0,1]): Active_Nodes.append(key)

    return Active_Nodes, Steady_State, Peak_Conc

def Continuous(states, Peak_Conc, thresh, interface):
    """
    Converts the discrete node status (ON or OFF)
    into corresponding continuous form using the
    peak concentration
    """
    changes = []
    for key in thresh:
        if states[key]:
            changes.append({"compartment" : interface[key],"species" : key })

    return changes

if __name__ == '__main__':

    #states = Run("p53_network.json", 
