#!/usr/bin/env python

import sys, json, copy, pickle
import itertools, random, time
from multiprocessing import Pool
from system_solver import SystemSolver
import numpy as np
import boolean2

statestr = lambda state, sep = '' : sep.join(map(str, state))

def DictListUpdate(Dict, key, value):
    if key in Dict:
        Dict[key].append(value)
    else:
        Dict[key] = [value]

def get_state(model, repeat = True):
    
    index, size = model.detect_cycles()
    if size == 0:
        if repeat:
            model.iterate(steps = 30)
            index, size = model.detect_cycles()
            if size == 0:
                raise IndexError
        else:
            initial_state = map(int, model.first.values())
            final_state = map(int, model.last.values())
            k = ( statestr(final_state), "none")
            return (k, statestr(initial_state))
            
                
    elif size == 1:
        initial_state = map(int, model.first.values())
        final_state = map(int, model.last.values())
        k = (statestr(final_state), "fixed")

        return (k, statestr(initial_state))
    else:
        initial_state = map(int, model.first.values())
        cycles = zip(*[map(int, elem[-size:]) for elem in model.data.values()])
        k = ( tuple( statestr(elem) for elem in cycles ), size, "cycle" ) 
        return (k, statestr(initial_state))

def boolnetrun(args):

    Combined_Rule, nodes, init_state, ii = args
    #print "Step %i, initial state %s" % (ii + 1, str(init_state))
    model = boolean2.Model(Combined_Rule, mode = "sync")

    try:
        model.initialize(defaults = dict(zip(nodes, init_state)))
        model.iterate(steps = 100)
        k, state_string = get_state(model)
        return (k, state_string)

    except IndexError:
        initial_state = map(int, model.first.values())
        final_state = map(int, model.last.values())
        k = ( statestr(final_state), "none")
        return (k, statestr(initial_state))

    
class BoolSolver(SystemSolver):
    """
    This class solves a boolean model
    by importing the network configuration
    and evolving it to next state
    """

    def __init__(self, inputfile, parameter):
        SystemSolver.__init__(self, inputfile, parameter)
        self.current_step = 0
        self.num_runs = 0
        self.num_data = 0
        self.job_status = "not started"

    def Readfile(self):
        with open(self.inputfile) as fp: self.network = json.load(fp)["network"]
        self.initial_network = copy.deepcopy(self.network)
        self.states = dict((key,val["initial_state"]) for key, val in self.network.items())

    def __Modify_Network(self):
        return dict(((key, value['base'],value['initial_state']),value['input_nodes']) for key, value in self.network.items())

    def Initialize_Data(self, Lose_Memory = False):
        """
        Initializes the boolean model. The parameter Lose_Memory
        determines whether this is initializing both the model and
        the data or just losing the memory of the previous step but
        keeps the data
        """
        self.all_states = [copy.deepcopy(self.states)]
        for key, value in self.parameter["states"].items():
            self.network[key]["initial_state"] = value
        if not Lose_Memory:
            self.data = { key : [value["initial_state"]] for key,value in self.network.items() }
            self.data_indices = []
        print "Initialize Data " , ','.join(["%s = %s" % (key, value["initial_state"]) for key, value in self.network.items()])

    def Change_Parameters(self):
        """
        Changes network parameters
        """
        self.parameter["value_change"] = []
        for key, value in self.parameter["states"].items():
            oldval = self.states[key]
            self.states[key] = value
            self.network[key]["initial_state"] = value
            self.parameter["value_change"].append((key, oldval, self.states[key]))
        for key, value in self.parameter["bases"].items():
            self.network[key]["base"] = value
        #self.Initialize_Data()

    def Solve(self):
        mod_network = self.__Modify_Network().items()
        for key, val in mod_network:
            species, weights = zip(*val)
            sumelem = sum(map(lambda xi,yi : xi*yi, [self.network[j]["initial_state"] for j in species],weights)) if species[0] != "None" else 0 + key[1]
            self.states[key[0]] = 1 if sumelem > 0 else (0 if sumelem < 0 else self.states[key[0]])
            #self.states[key[0]] = 1 if sumelem > 0 else 0
            print key, sumelem, self.states[key[0]], species, weights
        for node, state in self.states.items():
            self.network[node]["initial_state"] = state
        self.num_runs += 1
        self.job_status = "completed"
        
    def Get_Data(self):

        if self.job_status != "completed":
            raise Exception("Job still %s" % self.job_status)
        if self.num_data >= self.num_runs:
            raise Exception("Data already updated with latest run")
        if self.num_data < self.num_runs - 1:
            raise Exception("Data lagging by more than one runs, restart simulation")

        self.all_states.append(copy.deepcopy(self.states))
        for key, value in self.states.items():
            self.data[key].append(value)
        self.num_data += 1


class BoolNetSolver(BoolSolver):
    """
    This is a subclass of general BoolSolver that reimplements the `Solve`
    and Get_Data methods
    """
    def __init__(self, inputfile, parameters):
        BoolSolver.__init__(self, inputfile, parameters)
    
    def __Get_Interaction_Matrix(self):

        """
        Function to return the interaction matrix
        for a given network configuration
        """
        species_list = sorted(self.network.keys())
        interaction_matrix = np.zeros((len(species_list), len(species_list)), dtype='int32')

        #Populate the interaction matrix using the json file
        np.fill_diagonal(interaction_matrix, 1)
        for ii, species in enumerate(species_list):
            for elem in self.network[species]['input_nodes']:
                if elem[0] != 'None':
                    interaction_matrix[ii, species_list.index(elem[0])] = elem[1]

        return interaction_matrix

    def _GenerateInit(self):
        """
        Generates the initial conditions of the Boolean
        """
        Init_Cond_True = Init_Cond_False = ''
        for key, value in self.network.items():
            if value["initial_state"]:
                Init_Cond_True += key + ' = '
            else:
                Init_Cond_False += key + ' = '
        Init_Cond = Init_Cond_True + 'True' + '\r\n' + Init_Cond_False + 'False'

        return Init_Cond

    def _GenerateRules(self, Outfile = ""):
        """
        Generates the booleannet text rules from an input
        network configuration
        """
        Combined_Rule = []
        Inner = lambda x, y : sum([ i * j for i,j in zip(x,y) ])
        Next_State = lambda sumelem,node : (sumelem > 0) + (sumelem == 0) * node

        for key, value in sorted(self.network.items(), key = lambda x : x[0]):

            node_rule = []
            for elem in itertools.product([False, True], repeat = len(value["input_nodes"])):
                species, weights = zip(*value["input_nodes"])
                if species[0] == "None":
                    input_nodes = False
                    continue
                else:
                    input_nodes = True
                nodestates = zip(species, elem)
                sumelem = Inner(map(int, elem), weights) + value["base"]
                for node in [0, 1]:
                    next_node_state = Next_State(sumelem, node)
                    if next_node_state == 1:
                        input_nodes = [ nodelem if weight > 0 else "not " + nodelem for nodelem, weight in nodestates ]
                        temp_node_str = '( %s )' % ' and '.join(input_nodes)
                        if node:
                            if temp_node_str not in node_rule:
                                input_nodes.append(key)
                                node_rule.append('( %s )' % ' and '.join(input_nodes))
                        else:
                            node_rule.append('( %s )' % ' and '.join(input_nodes))

            if input_nodes:
                Combined_Rule.append('1: ' + key + ' *= ' + ' or '.join(node_rule))

        text = '\r\n'.join(Combined_Rule)

        if Outfile != "":
            with open(Outfile, "w") as fp: fp.write(text)

        return text
                        
                

    def __GenerateTable(self, interaction_matrix):
        """
        This function obtains text based rules for booleannet
        module by analyzing the interaction matrix
        """
        species = sorted(self.states.items())

        States = [ "%s = %s" % (key, bool(value)) for key, value in species ]
        Rules = []

        for ii, row in enumerate(interaction_matrix):
            pos = np.nonzero([elem for jj, elem in enumerate(row) ])
            if len(pos[0]) > 0:
                input_species = [ species[jj][0] if row[jj] > 0 else "(not %s)" % species[jj][0] for jj in pos[0] if jj != ii ]
                input_species_weights = [ (species[jj][0],species[jj][1]) for jj in pos[0] if jj != ii ]
                sorted_input_species = [ elem[0] for elem in sorted(input_species_weights, key = lambda x : x[1]) ]
                if len(input_species) > 0:
                    for kk, elem in enumerate(sorted_input_species):
                        for subelem in input_species:
                            if elem in subelem:
                                sorted_input_species[kk] = subelem
                                break
                    Op = " or " if all(row[pos] > 0) and not all(row[pos][1:] == row[pos][:-1]) else " and "
                    Rules.append("1: %s *= " % species[ii][0] + Op.join(sorted_input_species))
        text = "\n".join(States) + "\n\n" + "\n".join(Rules)

        return text

    def Initialize_Data(self, Rulefile="",Writefile="no",useMatrix=False, Lose_Memory = False):
        BoolSolver.Initialize_Data(self, Lose_Memory = Lose_Memory)

        if Rulefile == "":
            if useMatrix:
                interaction_matrix = self.__Get_Interaction_Matrix()
                self.Rules = self.__GenerateTable(interaction_matrix)
            else:
                self.Rules = self._GenerateInit() + '\r\n' + self._GenerateRules()
            if Writefile == "yes":
                Rulefile = raw_input("Give the filename: ")
                with open(Rulefile, "w") as fp: fp.write(self.Rules)
        else:
            with open(Rulefile) as fp: self.Rules = fp.read()
        self.model = boolean2.Model(self.Rules, mode = "sync")
        self.model.initialize()

    def Writefile(self):
        with open(self.tmpfile,"w") as fp: fp.write(self.Rules)
        
    def Solve(self, steps = 1):
        self.model.iterate(steps = steps)

    def State_Update(self):
        for key, value in self.states.items():
            self.network[key]["initial_state"] = value

    def Get_Data(self, ignore_steady = True):
        """
        This module collects the data from the
        booleannet run. The flag ignore_steady specifies
        whether to ignore if no steady state such as
        fixed point or cycle are found
        """

        index, size = self.model.detect_cycles()
        if size == 0:
            if not ignore_steady:
                #Final state not found raise exception
                raise Exception("No final state found for initial state %s" % str(self.state))
            else:
                final_state = self.model.states[-1:]
                initial_state = self.model.first.fp()
        else:
            final_state = self.model.states[-size:]
            initial_state = self.model.first.fp()

        start_index = len(self.data[self.data.keys()[0]]) - 1 if len(self.data[self.data.keys()[0]]) > 0 else 0
        final_state_mod = [elem.split('=') for elem in str(final_state[0]).lstrip('State: ').split(', ')]
        self.states.update(dict([ [elem[0], int(elem[1] == "True")] for elem in final_state_mod ]))
        for key, value in self.states.items():
            self.data[key].append(value)
        end_index = len(self.data[self.data.keys()[0]]) - 1 if len(self.data[self.data.keys()[0]]) > 0 else 0
        self.data_indices.append((start_index, end_index))
        self.num_data += 1


    def Attractor_Analysis(self, Outfile = "", Random = False, N = 1000, Parallel = True):
        """
        Performs an attractor analysis of the whole network
        Should be used independently of the other methods
        """
        nodes = self.network.keys()
        #self.Rules = self._GenerateInit() + '\r\n' + self._GenerateRules()
        Combined_Rule = self._GenerateInit() + '\r\n' + self._GenerateRules()
        States = {}

        Initial_State_Space = list(itertools.product([False, True], repeat = len(nodes)))
        if not Random:
            Initial_States = Initial_State_Space
        else:
            Initial_States = [Initial_State_Space[ii] for ii in random.sample(xrange(0, len(Initial_State_Space)), N)]

        results = []
        start_time = time.time()

        if Parallel:
            joblist = [ (Combined_Rule, nodes, init_state, ii) for ii, init_state in enumerate(Initial_States) ]
            pool = Pool(4)
            results = pool.map(boolnetrun, joblist)
            pool.close()
            pool.join()
        else:
            for ii, init_state in enumerate(Initial_States):
                results.append(boolnetrun((Combined_Rule, nodes, init_state, ii)))

        for key, value in results:
            DictListUpdate(States, key, value)

        elapsed_time = time.time() - start_time
        print "Elapsed Time = %f mins or %i secs for steps %i" % ( elapsed_time/60, elapsed_time, N )

        if Outfile != "":
            with open("%s.pickle" % Outfile, "wb") as fp: pickle.dump({"States" : States, "Nodes" : self.model.first.keys() }, fp)

        return States

    def Initial_Run(self, data = {}, updatemodel = True, steps = 1):
        """
        Performs an initial run of the model with specified
        initial conditions
        """
        if not updatemodel:
            self.parameter["states"].update(data)
        self.Readfile()
        self.Initialize_Data()
        self.Change_Parameters()
        self.Solve(steps = steps)
        self.Get_Data()

    def Equilibrium_Run(self, data = {}, updatemodel = True, steps = 1):
        """
        Performs a normal run to equilibrium
        """
        self.parameter["states"] = data
        self.Change_Parameters()
        self.Solve(steps = steps)
        self.Get_Data()


        
if __name__ == '__main__':

    usage = "python boolsolve.py networkfile changefile"
    if len(sys.argv) < 3:
        print usage
        sys.exit(1)
    networkfile = sys.argv[1]
    changefile = sys.argv[2]
    with open(changefile) as fp: parameters = json.load(fp)
    boolrun = BoolSolver(networkfile, parameters)
    boolrun.Readfile()
    boolrun.Initialize_Data()
    boolrun.Change_Parameters()
    for _ in range(5):
        boolrun.Solve()
        boolrun.Get_Data()

    boolnetrun = BoolNetSolver(networkfile, parameters)
    boolnetrun.Readfile()
    boolnetrun.Initialize_Data()
    boolnetrun.Change_Parameters()
    boolnetrun.Solve()
    boolnetrun.Get_Data()
