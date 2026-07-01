#!/usr/bin/env python

"""
This script is used to setup, run and collect data in batches
for a set of sweep conditions. By providing different flags and
running this over regular intervals, this same script can be
used to setup runs for a specific patient and drug combinations,
submit runs to PBS cluster, monitor the running jobs and update
their status and collect all the data after the runs are completed
and cleanup. This script uses the `SimulationBatch` class from
the [`job_setup.py`](job_setup.m.html) script which contains the
PBS specific details.

Example Run
-----------
This script is invoked with specific flags for specific functions.
When running for the first time, it is run with the `-i` flag as
below

    $ python batch_setup.py -i Run_Info_5XIHQG_Dox_Vincristine.json

The above command runs the script for patient 5XIHQG with the
drugs Dox and Vincristine. To submit the jobs and monitor them
the command below can be run at regular intervals

    $ python batch_setup.py Run_Info_5XIHQG_Dox_Vincristine.json >> 5XIHQG_Dox_Vincristine.log

This script should only be run after running the `preprocessor.py`
script which generates the input file
`Run_Info_5XIHQG_Dox_Vincristine.json`.

Input Files
-----------
The main input files needed by the script are as follows

- `Run_Info_<Patient-ID>_<Drug-Combo>.json` The first file is a
json file that is generated from the main file `Run_Info.json`
by the `preprocessor.py` script. This contains the patient
specific adjustments based on miRNA data and the drug dosages.
- [`Pbs_Setup.json`](../hss/interface/Pbs_Setup.json) This file contains information
about the specific run parameters for the PBS nodes such as number
of nodes, processors per node and walltime.

Output Data
-----------
The output from this script are

- `Sweepfile_<run-id>.json` where `run-id` is the particular sweep
id made from patient id and drug combination. This file contains
the specific parameters for the sweep and command line strings
used to submit the jobs. For each run of this script this file
gets updated with information about specific job.
- `Model_Data_<run-id>.pickle` This is a python pickle file
containing data from the simulation which will be used by the
post processing scripts.
- `Cell_Fates_<run-id>.json` This contains the cell fate data for
different sweep conditions.

Dependencies
------------

- Python >= 2.7
- Local modules [`odesolve`](odesolve.m.html), [`boolsolve`](boolsolve.m.html), [`sweep`](sweep.m.html), [`job_setup`](job_setup.m.html)

"""

import os, sys, json
import pickle, copy
import itertools, random, math
import multiprocessing as mp
from job_setup import SimulationBatch
from optparse import OptionParser

script_dirs = ["solver", "interface", "visualization", "utils", "../tests"]
'''Path to the main scripts used for solving the models and other utility scripts'''

for dirs in script_dirs:
    sys.path.append(os.path.abspath("../%s" % dirs))

import odesolve, boolsolve, sweep
import tools

def Batch_Build(writefile = "", demo = False):
    """
    Create the list of arguments for performing the batch
    run
    """
    arglist = []
    argdict = {}
    Combined_Space = list(enumerate(itertools.product(Sweep_Space, Memory, init_states)))

    # If running a demo, limit the variable space to be explored in this batch run to just 4 of its many possible states
    Spacelist = Combined_Space[:4] if demo else Combined_Space

    # If a radiation dosage is included in the sweep configuration, proportionally activate ATM in the hybrid model
    if Run_Info["Radiation"]["dosage"] > 0:
        atm_activation_weight = 1 - math.exp(-Run_Info["Radiation"]["alpha"]*float(Run_Info["Radiation"]["dosage"]))
        weighted_choice_list = [(0, 1 - atm_activation_weight),(1, atm_activation_weight)]
        atm_activation_state = [tools.weighted_choice(weighted_choice_list) for _ in range(len(Spacelist))]
    else:
        atm_activation_state = [0 for _ in range(len(Spacelist))]

    # Create list of jobs in batch, one for each state in the combined list of possible initial states
    for num, loopelem in Spacelist:
        elem, updatemodel, init_state = loopelem
        arglist.append((num, Unconstrained_Nodes, init_state, elem, updatemodel,atm_activation_state[num]))
        argdict[num] = {}
        argdict[num]["args"] = (num, Unconstrained_Nodes, init_state, elem, updatemodel,atm_activation_state[num])
        argdict[num]["status"] = "not submitted"

    # Write list to file
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

def Batch_Collect(resultfile, writefile = ""):
    """
    Collects the results from a batch run.
    results must be a dictionary with model id as key and the
    data as value
    """
    with open(resultfile) as fp: results = pickle.load(fp).values()
    Cell_Fates = { "cell_death" : [], "cell_growth" : [], "cell_senescence" : [] }
    Cell_Fates_Total = { "cell_death" : 0.0, "cell_growth" : 0.0, "cell_senescence" : 0.0 }
    Cell_Fates_Lookup = { "cell_death" : [], "cell_growth" : [], "cell_senescence" : [] }
    Cell_Fates_Total_Lookup = { "cell_death" : 0.0, "cell_growth" : 0.0, "cell_senescence" : 0.0 }
    Modelstates = { key : [] for key in Run_Info["models"].keys() }
    total = 0
    total_lookup = 0

    for result in results:
        for key, value in result.items():
            Modelstates[key].append(value)
            if "cell_fate" in value:
                for k, v in value["cell_fate"].items():
                    Cell_Fates[k].append(v)
                    Cell_Fates_Total[k] += v
                    total += v
                for k, v in value["cell_fate_lookup"].items():
                    Cell_Fates_Lookup[k].append(v)
                    Cell_Fates_Total_Lookup[k] += v
                    total_lookup += v

    Cell_Fate_Probabilities = { key : float(value)/total for key,value in Cell_Fates_Total.items() }
    Cell_Fate_Probabilities_Lookup = { key : float(value)/total_lookup for key,value in Cell_Fates_Total_Lookup.items() }

    if writefile != "":
        writefile = os.path.splitext(writefile)[0] + ".json"
        with open(writefile, "w") as fp: json.dump({"Cell_Fates" : Cell_Fates, "Cell_Fate_Probabilities" : Cell_Fate_Probabilities, "Cell_Fates_Lookup" : Cell_Fates_Lookup, "Cell_Fate_Probabilities_Lookup" : Cell_Fate_Probabilities_Lookup}, fp)

    return Modelstates, Cell_Fate_Probabilities, Cell_Fate_Probabilities_Lookup

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

def Unconstrained(boolmodel, interfaces, restricted):
    """
    This function determines the list of unconstrained nodes
    from a boolean model
    """
    Constrained_Nodes = set(interfaces) | set(restricted) | set(boolmodel["changes"]["states"].keys())
    Unconstrained_Nodes = set(boolmodel["network"].keys()) - Constrained_Nodes

    return list(Unconstrained_Nodes)

if __name__ == '__main__':

    # Parse command line arguments
    usage = "usage: %prog [options] jsonfile"
    parser = OptionParser(usage = usage)
    parser.set_defaults(initial_run = False, demo_run = False)
    parser.add_option("-i", "--initial-run", dest = "initial_run", action = "store_true", help = "Use this option when performing initial setup")
    parser.add_option("-d", "--demo-run", dest = "demo_run", action = "store_true", help = "Use this option when performing demo run")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error(usage)
    elif not os.path.isfile(args[0]):
        parser.error("File %s not found" % args[0])
    else:
        with open(args[0]) as fp: Run_Info = json.load(fp)

    # Initialize variables for batch run
    Sweep_Data = Run_Info["sweeps"]["chenode"]
    Sweep_Space = sweep.Generate_Sweeps(Sweep_Data)
    Memory = [True] # [True, False]
    sweepfile = "Sweepfile_%s.json" % Run_Info["run_id"]
    jobfile = "Slurm_Setup.json" # "Pbs_Setup.json"
    sweep_limit = 4

    # Set up files for batch run
    if options.initial_run:
        # Remove status files from previous run of this batch if they exist
        if os.path.isfile(Run_Info["run_id"] + ".status"):
            os.remove(Run_Info["run_id"] + ".status")

        #  Determine unconstrained nodes
        for key, value in Run_Info["models"].items():
            if value["type"] == "boolean":
                print value
                with open(value["file"]) as fp: boolmodel = json.load(fp)
                interfaces = [elem[0] for elem in value["interfaces"][0]["nodes"]]
                restricted = value["Restricted_Nodes"]
                Unconstrained_Nodes = Unconstrained(boolmodel, interfaces, restricted)
                init_states = Initial_States(Unconstrained_Nodes, limit = sweep_limit)
                break

        # Set up batch to iterate over uncontrained node values
        arglist = Batch_Build(writefile = sweepfile, demo = options.demo_run)

    # Check on batch run
    if os.path.isfile(Run_Info["run_id"] + ".status"):
        # Collect and report results if all jobs are complete
        with open(Run_Info["run_id"] + ".status") as fp: message = fp.read()
        if not os.path.isfile("Cell_Fates_%s.json" % Run_Info["run_id"]):
            Modelstates, Cell_Fate_Probabilities, Cell_Fate_Probabilities_Lookup = Batch_Collect("Model_Data_%s.pickle" % Run_Info["run_id"], writefile = "Cell_Fates_%s.json" % Run_Info["run_id"])
        else:
            with open("Cell_Fates_%s.json" % Run_Info["run_id"]) as fp: Cell_Fate_Probabilities = json.load(fp)["Cell_Fate_Probabilities"]
            with open("Cell_Fates_%s.json" % Run_Info["run_id"]) as fp: Cell_Fate_Probabilities_Lookup = json.load(fp)["Cell_Fate_Probabilities_Lookup"]
        print "Run completed for %s, cell fate probabilities:" % Run_Info["run_id"]
        print "Cell Kill = %(cell_death)s, Cell Growth = %(cell_growth)s, Cell Senescence = %(cell_senescence)s" % Cell_Fate_Probabilities
        print "Lookup: Cell Kill = %(cell_death)s, Cell Growth = %(cell_growth)s, Cell Senescence = %(cell_senescence)s" % Cell_Fate_Probabilities_Lookup

    else:
        # Continue running incomplete jobs and update job statuses
        batch = SimulationBatch(Run_Info["run_id"], sweepfile, jobfile, args[0])
        batch.update()
        batch.write(sweepfile)
