---
title: Combined Run
header-includes:
    <link href="styles.css" rel="stylesheet"/>
---

# Objective

This script aims to perform batch runs of two or more models of
different types such as continuous time ordinary differential
equations and discrete time boolean rules. Currently, this only
supports two or more models represented by continuous time ODE
(in COPASI xml/SBML format) and discrete time Boolean model (in a
custom json format). One can specify a sweep space (high/low
levels of species such as growth factors, run memory etc) for the
ODE and a list of constrained nodes for the boolean. The output
is in the form of cell fate probabilities for the system and also
time course data for ODE and boolean versions of the models.

# Data

## Input Data

The main input is in a `json` format. There are two main
categories of input

`models` This gives the individual models, their ids, type of
models and all the information needed to run them. A schema for
the model is in this [file](Run_Info_Schema.html)

Each model has the following main components

a) type - What type of model it is - currently only supports ode
or boolean

b) file - Path to the file containing the model configuration

c) conv - Only required for SBML ODE models where a conversion
factor is required to transform the concentrations

d) initialize - Again only required for ODE and it specifies the
set of parameters that are to be changed in the input file.

e) plot parameters - What specific parameters are to be plotted
in the ODE model

f) sim parameters - The specific simulation parameters which need
to be altered.

g) interfaces - This specifies the interface that this model
shares with other models in the system including the type of the
current model and what nodes are shared. This information will be
read by other solvers when they make any sort of adjustments to
the interface nodes.

`sweeps` This category specifies the sweep space over
which the combination needs to be run and averaged. Currently
this is only supported for ODE.

`model_runs` This specifies the sequence of model runs in the
form of a list of the model ids.

`run_id` An unique id for the type of run

`steps` The number of steps the combination is to be run.

`Plots` A flag indicating whether to plot individual time courses
for specific models.

## Output Data

This depends on the mode of run - ode only, boolean only, ode and
boolean together.

For the combination of models the following quantities are output:

`Cell_Fate_Probabilities` This gives the predicted cell fate
probabilities for the combined run.

`Modelstates` This gives the simulation data for each model and
is keyed by the model id used in the input json file.

The above quantities are written in a pickle file named with the
prefix `Simulation_Data_` in the same directory.

For other modes the data are as below

`Odestates` (List) This is a list of dictionaries containing the
data for each element of the sweep space.

`odedata` (Dictionary) Each element of Odestates is a dictionary
which contains the data and parameters for the particular model
instance. The `data` is a dictionary of time course values.

`Boolstates` (List) This is a list of dictionaries containing
data for each element of sweep space.

`booldata` (Dictionary) This contains the discrete state data,
parameters of individual sweeps and the cell fate over all the
initial states.


## Functions/Classes

### Unconstrained()

**Function Signature**

```
def Unconstrained(boolmodel, interfaces):
```

**Input Parameters**

`boolmodel` - Dictionary containing the details of the boolean
model.

`interfaces` - Dictionary containing the interface nodes of the
boolean.

**Output Parameters**

`Unconstrained_Nodes` - List of nodes which are not constrained
to be on or off

**Example Run**

```
>>> pprint(boolmodel)
{u'changes': {u'bases': {u'ATM': 1}, u'states': {u'ATM': 0, u'CDK1': 1}},
 u'indicator': {u'cell_death': {u'CASP9': 1, u'CDK2': 0},
                u'cell_growth': {u'CASP9': 0, u'CDK2': 1}},
 u'network': {u'AKT_P': {u'base': 1,
                         u'initial_state': 0,
                         u'input_nodes': [[u'PTEN', -2]]},
              u'ARF': {u'base': -1,
                       u'initial_state': 0,
                       u'input_nodes': [[u'TP53', -2],
                                        [u'WIP1', -1],
                                        [u'E2F1', 1],
                                        [u'ERK_PP', 1]]},
...
>>> print(interfaces)
[u'ERK_PP', u'AKT_P', u'Raf_P', u'PTEN']
>>> Unconstrained_Nodes = Unconstrained(boolmodel, interfaces)
>>> print(Unconstrained_Nodes)
[u'TP53', u'E2F1', u'WIP1', u'CDKN1A', u'RB1', u'CASP9', u'CCNG1', u'CDK2', u'BAX', u'ARF', u'MDM2', u'MDM4', u'BCL2']
```

### Initial\_States()

This function prepares the initial sweep space for a combined
setup using the list of unconstrained nodes.

**Function signature**

```
def Initial_States(Unconstrained_Nodes, limit = 4):
```

**Input Parameters**

`Unconstrained_Nodes` A list of unconstrained nodes based on
which the initial sweep space will be determined.

`limit` -  Specifies how many cores have to be considered in
total.

**Output Parameters**

`init_states` - List of all the initial states of the model

**Example Run**

```
>>> Unconstrained_Nodes
[u'TP53', u'E2F1', u'WIP1', u'CDKN1A', u'RB1', u'CASP9', u'CCNG1', u'CDK2', u'BAX', u'ARF', u'MDM2', u'MDM4', u'BCL2']
>>> init_states = cr.Initial_States(Unconstrained_Nodes, limit = 3)
>>> pprint(init_states)
[(0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0),
 (0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0),
 (0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1),
 (0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0)]
>>> init_states = cr.Initial_States(Unconstrained_Nodes, limit = 4)
>>> pprint(init_states)
[(0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0),
 (1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0),
 (1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1),
 (1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0),
 (1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1),
 (1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0),
 (0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0),
 (0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1)]

```


### Batch\_Build()

**Function Signature**

```
def Batch_Build(writefile = ""):
```

**Description**

This function prepares a list of arguments to be supplied to the
`Coupled_Loop()` function. The list of arguments is the entire
sweep space of the hybrid model.

**Input Parameters**

`writefile` If not empty should provide the name of the output
json file where all the sweep arguments will be written for later
reference.

**Global Parameters**

`Sweep_Space` (from main) The list of all the space of parameters
over which the sweep is to be run. Currently this is only
supported for ODE.

`init_states` (from main) The list of all initial states based
on the unconstrained nodes. Currently this is only supported for
Boolean.

`Memory` (from main) List containing the with and without memory
conditions

**Local Parameters**

`Combined_Space` The list of all parameter space combining the
sweep space, memory and the initial states

`argdict` The dictionary of all sweep conditions keyed by their
numeric id.

**Output Parameters**

`arglist` List of all the arguments to be passed to the
`Coupled_Loop` function

**Output Files**

If `writefile` is not `""` writes a json file using the provided
name.

**Example Run**

```python
Dirname = ""
with open("Run_Info_New.json") as fp: Run_Info = json.load(fp)
Sweep_Data = Run_Info["sweeps"]["chenode"]
Sweep_Space = sweep.Generate_Sweeps(Sweep_Data)

#Determine unconstrained nodes
for key, value in Run_Info["models"].items():
	if value["type"] == "boolean":
		with open(value["file"]) as fp: boolmodel = json.load(fp)
		interfaces = value["interfaces"][0]["nodes"]
		Unconstrained_Nodes = Unconstrained(boolmodel, interfaces)
		init_states = Initial_States(Unconstrained_Nodes)
		break
				
Writefile = os.path.join(Dirname, "Data_Id.json")
arglist = Batch_Build(writefile = Writefile)
```

The output after running this script is as below

```
>>> for elem in arglist[:5]:
...     print elem
... 
(0, [u'TP53', u'E2F1', u'WIP1', u'CDKN1A', u'RB1', u'CASP9', u'CCNG1',
u'CDK2', u'BAX', u'ARF', u'MDM2', u'MDM4', u'BCL2'], (0, 0, 1, 0, 1,
0, 0, 0, 1, 0, 1, 1, 1), [{u'Paramtype': u'Initial Species Values',
u'substitute': {u'compartment': u'medium', u'species': u'EGF'},
u'value': 1e-09}], True) (1, [u'TP53', u'E2F1', u'WIP1', u'CDKN1A',
u'RB1', u'CASP9', u'CCNG1', u'CDK2', u'BAX', u'ARF', u'MDM2', u'MDM4',
u'BCL2'], (1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0), [{u'Paramtype':
u'Initial Species Values', u'substitute': {u'compartment': u'medium',
u'species': u'EGF'}, u'value': 1e-09}], True) (2, [u'TP53', u'E2F1',
u'WIP1', u'CDKN1A', u'RB1', u'CASP9', u'CCNG1', u'CDK2', u'BAX',
u'ARF', u'MDM2', u'MDM4', u'BCL2'], (1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1,
0, 1), [{u'Paramtype': u'Initial Species Values', u'substitute':
{u'compartment': u'medium', u'species': u'EGF'}, u'value': 1e-09}],
True) (3, [u'TP53', u'E2F1', u'WIP1', u'CDKN1A', u'RB1', u'CASP9',
u'CCNG1', u'CDK2', u'BAX', u'ARF', u'MDM2', u'MDM4', u'BCL2'], (1, 0,
1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1), [{u'Paramtype': u'Initial Species
Values', u'substitute': {u'compartment': u'medium', u'species':
u'EGF'}, u'value': 1e-09}], True) (4, [u'TP53', u'E2F1', u'WIP1',
u'CDKN1A', u'RB1', u'CASP9', u'CCNG1', u'CDK2', u'BAX', u'ARF',
u'MDM2', u'MDM4', u'BCL2'], (0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0),
[{u'Paramtype': u'Initial Species Values', u'substitute':
{u'compartment': u'medium', u'species': u'EGF'}, u'value': 1e-09}],
True)
>>> os.system('head -10 Data_Id.json')
{
    "0": [
        [
            "TP53", 
            "E2F1", 
            "WIP1", 
            "CDKN1A", 
            "RB1", 
            "CASP9", 
            "CCNG1", 
0
```

### Batch\_Run()

**Function Signature**

```
def Batch_Run(arglist, Parallel = False):
```

**Input Parameters**

`arglist` This is a list of arguments obtained from the
`Batch_Build()` function shown above.

`Parallel` A keyword argument that specifies whether the runs are
to be made in parallel or not.

**Output Parameters**

`results` Holds the results of the simulation for both run modes
and returns it to the caller.

**Example Run**

Main Section Code

```python
Dirname = ""
with open("Run_Info_New.json") as fp: Run_Info = json.load(fp)
Sweep_Data = Run_Info["sweeps"]["chenode"]
Sweep_Space = sweep.Generate_Sweeps(Sweep_Data)

#Determine unconstrained nodes
for key, value in Run_Info["models"].items():
	if value["type"] == "boolean":
		with open(value["file"]) as fp: boolmodel = json.load(fp)
		interfaces = value["interfaces"][0]["nodes"]
		Unconstrained_Nodes = Unconstrained(boolmodel, interfaces)
		init_states = Initial_States(Unconstrained_Nodes)
		break

arglist = Batch_Build(writefile = os.path.join(Dirname, "Data_Id.json"))
quit()
```
Code output

```
$ python -i combined_run.py
Traceback (most recent call last):
  File "combined_run.py", line 262, in <module>
    quit()
  File "/home/alokendra/miniconda2/envs/csre/lib/python2.7/site.py", line 351, in __call__
    raise SystemExit(code)
SystemExit: None
>>> len(arglist)
32
>>> results = Batch_Run(arglist[:5])
In Coupled_Loop arguments num = 0, init_state = (1, 0, 0, 1, 0, 0, 0,
0, 1, 0, 0, 1, 0) In Coupled_Loop arguments num = 1, init_state = (0,
0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1) In Coupled_Loop arguments num = 2,
init_state = (0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1) In Coupled_Loop
arguments num = 3, init_state = (0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1,
1) In Coupled_Loop arguments num = 4, init_state = (1, 1, 1, 1, 1, 0,
1, 1, 1, 0, 0, 1, 1)
>>> def print_results(result):
...     for elem in results:
...         for key, value in elem.items():
...             print key, value
... 
>>> print_results(results)
rules Sample rules
choibool {'data': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
parameter {'p2': 0, 'p1': 0}
chenode {'data': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
rules Sample rules
choibool {'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
parameter {'p2': 2, 'p1': 1}
chenode {'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
rules Sample rules
choibool {'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
parameter {'p2': 4, 'p1': 2}
chenode {'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
rules Sample rules
choibool {'data': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}
parameter {'p2': 6, 'p1': 3}
chenode {'data': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}
rules Sample rules
choibool {'data': [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}
parameter {'p2': 8, 'p1': 4}
chenode {'data': [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}
>>> results = Batch_Run(arglist[:5], Parallel = True)
In Coupled_Loop arguments num = 0, init_state = (1, 0, 0, 1, 0, 0, 0,
0, 1, 0, 0, 1, 0) In Coupled_Loop arguments num = 1, init_state = (0,
0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1) In Coupled_Loop arguments num = 3,
init_state = (0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1) In Coupled_Loop
arguments num = 4, init_state = (1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1,
1) In Coupled_Loop arguments num = 2, init_state = (0, 0, 0, 1, 1, 1,
0, 1, 0, 1, 1, 0, 1)
>>> print_results(results)
rules Sample rules
choibool {'data': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
parameter {'p2': 0, 'p1': 0}
chenode {'data': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
rules Sample rules
choibool {'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
parameter {'p2': 2, 'p1': 1}
chenode {'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
rules Sample rules
choibool {'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
parameter {'p2': 4, 'p1': 2}
chenode {'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
rules Sample rules
choibool {'data': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}
parameter {'p2': 6, 'p1': 3}
chenode {'data': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}
rules Sample rules
choibool {'data': [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}
parameter {'p2': 8, 'p1': 4}
chenode {'data': [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}
```

The output shows that the runs are performed in both parallel and
serial mode of operation.

### Batch\_Collect()

**Function Signature**

```
def Batch_Collect(results, writefile = ""):
```

**Description**

This collects the simulation results from different elements of
the model sweep space and places them in a dictionary that is
keyed by the model id. It can optionally write this to a file.

**Input Parameters**

`results` This is the list of results obtained from the
`Batch_Run()` function.

`writefile` Optional keyword argument that specifies if the cell
fate probabilities are to be written to a file.

**Global Parameters**

`Run_Info["models"]` (from main): Gets the model ids for the different
models and uses it to populate the main dictionary

**Local Parameters**

`Cell_Fates` A dictionary for accumulating the different cell
fate values over the sweep space.

**Output Parameters**

`Modelstates` This holds the data for different models keyed by
the name of the model.

`Cell_Fate_Probabilities` This is a dictionary of the different
cell fates.

**Output File**

If `writefile` is not `""` it outputs a json file containing the
cell fates and cell fate probabilities.

**Example Run**

```
$ python -i combined_run.py
Traceback (most recent call last):
  File "combined_run.py", line 262, in <module>
    quit()
  File "/home/alokendra/miniconda2/envs/csre/lib/python2.7/site.py", line 351, in __call__
    raise SystemExit(code)
SystemExit: None
>>> results = Batch_Run(arglist[:3])
In Coupled_Loop arguments num = 0, init_state = (0, 0, 1, 1, 1, 1, 1,
1, 0, 1, 1, 1, 0) In Coupled_Loop arguments num = 1, init_state = (1,
1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0) In Coupled_Loop arguments num = 2,
init_state = (0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0)
>>> Dummy_Functions.print_results(results) choibool {'rules': 'Sample
rules', 'parameter': {'p2': 0, 'p1': 0}, 'data': [0, 1, 2, 3, 4, 5, 6,
7, 8, 9], 'cell_fate': {'cell_senescence': 2, 'cell_death': 1,
'cell_growth': 2}} chenode {'parameter': {'p2': 0, 'p1': 0}, 'data':
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]} choibool {'rules': 'Sample rules',
'parameter': {'p2': 2, 'p1': 1}, 'data': [1, 2, 3, 4, 5, 6, 7, 8, 9,
10], 'cell_fate': {'cell_senescence': 1, 'cell_death': 3,
'cell_growth': 1}} chenode {'parameter': {'p2': 2, 'p1': 1}, 'data':
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} choibool {'rules': 'Sample rules',
'parameter': {'p2': 4, 'p1': 2}, 'data': [2, 3, 4, 5, 6, 7, 8, 9, 10,
11], 'cell_fate': {'cell_senescence': 2, 'cell_death': 2,
'cell_growth': 1}} chenode {'parameter': {'p2': 4, 'p1': 2}, 'data':
[2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
>>> Modelstates, Cell_Fate_Probabilities = Batch_Collect(results)
>>> from pprint import pprint
>>> pprint(Cell_Fate_Probabilities)
{'cell_death': 0.4,
 'cell_growth': 0.26666666666666666,
 'cell_senescence': 0.3333333333333333}
>>> pprint(Modelstates)
{u'chenode': [{'data': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
               'parameter': {'p1': 0, 'p2': 0}},
              {'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
               'parameter': {'p1': 1, 'p2': 2}},
              {'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
               'parameter': {'p1': 2, 'p2': 4}}],
 u'choibool': [{'cell_fate': {'cell_death': 1,
                              'cell_growth': 2,
                              'cell_senescence': 2},
                'data': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                'parameter': {'p1': 0, 'p2': 0},
                'rules': 'Sample rules'},
               {'cell_fate': {'cell_death': 3,
                              'cell_growth': 1,
                              'cell_senescence': 1},
                'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                'parameter': {'p1': 1, 'p2': 2},
                'rules': 'Sample rules'},
               {'cell_fate': {'cell_death': 2,
                              'cell_growth': 1,
                              'cell_senescence': 2},
                'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                'parameter': {'p1': 2, 'p2': 4},
                'rules': 'Sample rules'}]}
>>> results = Batch_Run(arglist[:3], Parallel = True)
In Coupled_Loop arguments num = 0, init_state = (0, 0, 1, 1, 1, 1, 1,
1, 0, 1, 1, 1, 0) In Coupled_Loop arguments num = 1, init_state = (1,
1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0) In Coupled_Loop arguments num = 2,
init_state = (0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0)
>>> Dummy_Functions.print_results(results)
choibool {'rules': 'Sample rules', 'data': [0, 1, 2, 3, 4, 5, 6, 7, 8,
9], 'parameter': {'p2': 0, 'p1': 0}, 'cell_fate': {'cell_senescence':
0, 'cell_death': 4, 'cell_growth': 1}} chenode {'data': [0, 1, 2, 3,
4, 5, 6, 7, 8, 9], 'parameter': {'p2': 0, 'p1': 0}} choibool {'rules':
'Sample rules', 'data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 'parameter':
{'p2': 2, 'p1': 1}, 'cell_fate': {'cell_senescence': 4, 'cell_death':
1, 'cell_growth': 0}} chenode {'data': [1, 2, 3, 4, 5, 6, 7, 8, 9,
10], 'parameter': {'p2': 2, 'p1': 1}} choibool {'rules': 'Sample
rules', 'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 'parameter': {'p2':
4, 'p1': 2}, 'cell_fate': {'cell_senescence': 1, 'cell_death': 3,
'cell_growth': 1}} chenode {'data': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
'parameter': {'p2': 4, 'p1': 2}}
>>> Modelstates, Cell_Fate_Probabilities = Batch_Collect(results, writefile = "Cell_Fates_Test.json")
>>> pprint(Cell_Fate_Probabilities)
{'cell_death': 0.5333333333333333,
 'cell_growth': 0.13333333333333333,
 'cell_senescence': 0.3333333333333333}
>>> os.system('cat Cell_Fates_Test.json')
{"cell_senescence": 0.3333333333333333, "cell_death":
0.5333333333333333, "cell_growth": 0.13333333333333333}0
```

The runs show both parallel and serial versions and the cell
fates were created in the dummy function by randomly choosing it
between a specified range.

### Coupled_Loop

**Function Signature**

```
def Coupled_Loop(args):
```

**Description**

This function is a wrapper over the `Coupled_Run()` function
which runs a group of models together according to a specified
scheme. This performs the instantiation of individual models,
calling the `Coupled_Run()` function and collecting data and
converting it into a form that can be pickled. In the
parallel mode a copy of this function is run by each worker so we
do not have to worry about pickling classes and passing it
between processes as all of that is done in this function.

**Input Parameters**

`args` A 5 member tuple containing model specific values. This is
unpacked in the function to separate local variables (see below).

**Global Parameters**

`Run_Info` (from main) The main dictionary of run and model
specification read in the main section. It specifically accesses
the `model_run` part which contains information for individual
models.


**Local Parameters**

`num` The simulation number  
`Unconstrained_Nodes` The list of unconstrained nodes in the
boolean  
`init_state` The particular initial state chosen for this run  
`sweep_elem` The element of the sweep space (currently only
valid for ODE  
`updatemodel` A boolean flag indicating whether the final state
of a model will be used to initialize the run in the next step
(with or without memory)  

`boolmodel` A dictionary containing boolean model specific
information which was loaded in main.

`cell_fate` Dictionary containing the individual cell fate counts
over the specified number of steps.

`model_instance` List containing instances of the specific models
to be supplied to the `Coupled_Run()` function.

`oderun` A temporary storage for an instantiated ode solver.

`boolrun` A temporary storage for an instantiated bool solver.

**Output Parameters**

`model_data` Main dictionary containing the model specific data
which is returned to the batch function.

**Output File**

A pickle file with prefix `Sim_Data` containing data from
individual steps.

**Example Run**

```
>>> pprint(args)
(0,
 [u'TP53',
  u'E2F1',
  u'WIP1',
  u'CDKN1A',
  u'RB1',
  u'CASP9',
  u'CCNG1',
  u'CDK2',
  u'BAX',
  u'ARF',
  u'MDM2',
  u'MDM4',
  u'BCL2'],
 (1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0),
 [{u'Paramtype': u'Initial Species Values',
   u'substitute': {u'compartment': u'medium', u'species': u'EGF'},
   u'value': 1e-09,
   'value_change': (1e-07, 1e-09)},
  {u'Paramtype': u'Initial Species Values',
   u'substitute': {u'compartment': u'endosomal membrane',
                   u'species': u'ErbB2'},
   u'value': 0.0,
   'value_change': (2.549209595433081e-28, 0.0)},
  {u'Paramtype': u'Initial Species Values',
   u'substitute': {u'compartment': u'medium', u'species': u'EGF'},
   u'value': 1e-08,
   'value_change': (1e-09, 1e-08)}],
 True)
>>> model_data = combined_run.Coupled_Loop(args)
Initialize Data CDK1 = 0,TP53 = 0,ERK_PP = 1,E2F1 = 1,CCNG1 = 1,WIP1 =
0,CDKN1A = 0,ATM = 1,RB1 = 0,CASP9 = 0,PTEN = 1,CDK2 = 1,BAX = 0,ARF =
0,Raf_P = 0,AKT_P = 1,MDM2 = 1,MDM4 = 0,BCL2 = 1
>>> model_data.keys()
[u'choibool', u'chenode']
>>> for key in model_data:
...     print model_data[key].keys()
... 
['rules', 'parameter', 'data', 'cell_fate']
['parameter', 'data']
```

### Coupled_Run

**Function Signature**

```
def Coupled_Run(model_instances, reinitialize = False, updatemodel = True):
```

**Description**

This function runs the model combination for a single iteration
in a specified order. It gets the instances of the individual
models and uses that to perform both an initial run and
subsequent equilibration runs.

**Input Parameters**

`model_instances` A list of the model instances. The function
uses the order in this list to determine the run sequence

`reinitialize` A boolean flag that indicates whether the model
should be reinitialized or not before starting to solve the
model. This is typically only used during the initial run.

`updatemodel` Another boolean flag that indicates whether the
final state of the model will be used to reinitialize it or not.

**Global Parameters**

`Run_Info` This is the main dictionary containing the model
specific information.

**Local Parameters**

`Peak_Conc` This is a dictionary that is updated after the end of
the run of an ODE model to get the maximum concentration of a
species in the specified time period.

`continuous_data` This is used to store the converted continuous
concentrations of the interface species.

`discrete_data` This is used to store the converted discrete
concentrations of the interface species

`Interface_Data` (dict) This is used to store the information
related to the interface nodes for both models.

**Example Runs**

```
>>> Interface_Data = { key : Run_Info["models"][key]["interfaces"] for key in Run_Info["model_runs"] }
>>> pprint(Interface_Data)
{u'chenode': [{u'nodes': [[u'ERK_PP', u'cytoplasm'],
                          [u'AKT_P', u'cytoplasm'],
                          [u'Raf_P', u'cytoplasm'],
                          [u'PTEN', u'cytoplasm']],
               u'other': u'choibool',
               u'type': u'ode'}],
 u'choibool': [{u'nodes': [[u'ERK_PP', u'cytoplasm'],
                           [u'AKT_P', u'cytoplasm'],
                           [u'Raf_P', u'cytoplasm'],
                           [u'PTEN', u'cytoplasm']],
                u'other': u'chenode',
                u'type': u'boolean'}]}
>>> for key, value in Interface_Data.items():
...     for ii, elem in enumerate(value):
...         Interface_Data[key][ii]["nodes"] = dict(zip(map(tuple, elem["nodes"]), [0]*len(elem["nodes"])))
... 
>>> pprint(Interface_Data)
{u'chenode': [{u'nodes': {(u'AKT_P', u'cytoplasm'): 0,
                          (u'ERK_PP', u'cytoplasm'): 0,
                          (u'PTEN', u'cytoplasm'): 0,
                          (u'Raf_P', u'cytoplasm'): 0},
               u'other': u'choibool',
               u'type': u'ode'}],
 u'choibool': [{u'nodes': {(u'AKT_P', u'cytoplasm'): 0,
                           (u'ERK_PP', u'cytoplasm'): 0,
                           (u'PTEN', u'cytoplasm'): 0,
                           (u'Raf_P', u'cytoplasm'): 0},
                u'other': u'chenode',
                u'type': u'boolean'}]}
>>> model = model_instance[0]
>>> model["type"]
u'ode'
>>> combined_run.Solve(model["instance"], reinitialize = True, updatemodel = True)
>>> pprint(model["instance"].parameter)
[{u'Paramtype': u'Initial Species Values',
  u'substitute': {u'compartment': u'medium', u'species': u'EGF'},
  u'value': 1e-09,
  'value_change': (1e-07, 1e-09)},
 {u'Paramtype': u'Initial Species Values',
  u'substitute': {u'compartment': u'endosomal membrane',
                  u'species': u'ErbB2'},
  u'value': 0.0,
  'value_change': (2.549209595433081e-28, 0.0)},
 {u'Paramtype': u'Initial Species Values',
  u'substitute': {u'compartment': u'medium', u'species': u'EGF'},
  u'value': 1e-08,
  'value_change': (1e-09, 1e-08)}]
>>> name = Run_Info["model_runs"][0]
>>> combined_run.Interface(model["instance"], Interface_Data[name])
>>> Interface_Data["chenode"]
[{u'nodes': {(u'ERK_PP', u'cytoplasm'): [1270.78, 101637.0, 384254.0, 522678.0, 551372.0, 558141.0, 560516.0], (u'AKT_P', u'cytoplasm'): [0.000263169, 0.17437, 4.09559, 28.6766, 98.0575, 213.191, 340.704], (u'PTEN', u'cytoplasm'): [56095.8, 56029.8, 55912.7, 55863.6, 55893.7, 55933.0, 55960.9], (u'Raf_P', u'cytoplasm'): [593.443, 221.308, 52.0344, 15.0688, 8.65441, 6.20937, 4.81706]}, u'other': u'choibool', u'type': u'ode'}]
>>> Peak_Conc = {}
>>> for elem in Interface_Data[name]:
...     Peak_Conc.update({ key : max(value) for key, value in elem["nodes"].items() })
... 
>>> pprint(Peak_Conc)
{(u'AKT_P', u'cytoplasm'): 340.704,
 (u'ERK_PP', u'cytoplasm'): 560516.0,
 (u'PTEN', u'cytoplasm'): 56095.8,
 (u'Raf_P', u'cytoplasm'): 593.443}
>>> continuous_data = combined_run.Continuous(Interface_Data[key_other], Peak_Conc)
>>> continuous_data
{(u'ERK_PP', u'cytoplasm'): 184970.28, (u'AKT_P', u'cytoplasm'): 112.43232, (u'PTEN', u'cytoplasm'): 18511.614, (u'Raf_P', u'cytoplasm'): 195.83619000000002}
>>> pprint(continuous_data)
{(u'AKT_P', u'cytoplasm'): 112.43232,
 (u'ERK_PP', u'cytoplasm'): 184970.28,
 (u'PTEN', u'cytoplasm'): 18511.614,
 (u'Raf_P', u'cytoplasm'): 195.83619000000002}
>>> model = model_instance[1]
>>> model["instance"].parameter
{u'states': {u'TP53': 1, u'E2F1': 1, u'WIP1': 0, u'CDKN1A': 1,
>u'RB1': 1, u'CASP9': 0, u'CCNG1': 1, u'CDK2': 0, u'BAX': 1,
>u'ARF': 1, u'MDM2': 0, u'MDM4': 1, u'BCL2': 0}, u'bases':
>{u'ATM': 1}}
>>> model["instance"].parameter.update(discrete_data)
>>> model["instance"].parameter
{u'states': {u'TP53': 1, u'E2F1': 1, u'WIP1': 0, u'CDKN1A': 1,
u'RB1': 1, u'CASP9': 0, u'CCNG1': 1, u'CDK2': 0, u'BAX': 1,
u'ARF': 1, u'MDM2': 0, u'MDM4': 1, u'BCL2': 0}, u'PTEN': 1,
u'bases': {u'ATM': 1}, u'AKT_P': 1, u'ERK_PP': 1, u'Raf_P': 0} 
>>> combined_run.Solve(model["instance"], reinitialize = False, updatemodel = True)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/alokendra/Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/interface/combined_run.py", line 27, in Solve
    solver.Change_Parameters()
  File "/home/alokendra/Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/solver/boolsolve.py", line 101, in Change_Parameters
    oldval = self.states[key]
AttributeError: BoolNetSolver instance has no attribute 'states'
>>> combined_run.Solve(model["instance"], reinitialize = True, updatemodel = True)
Initialize Data  CDK1 = 0,TP53 = 1,ERK_PP = 1,E2F1 = 1,CCNG1 = 1,WIP1 = 0,CDKN1A = 1,ATM = 1,RB1 = 1,CASP9 = 0,PTEN = 1,CDK2 = 0,BAX = 1,ARF = 1,Raf_P = 0,AKT_P = 1,MDM2 = 0,MDM4 = 1,BCL2 = 0
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/alokendra/Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/interface/combined_run.py", line 32, in Solve
    solver.Readfile(filename = solver.tmpfile)
TypeError: Readfile() got an unexpected keyword argument 'filename'
>>> model = copy.deepcopy(boolmodel_orig)
>>> combined_run.Solve(model["instance"], reinitialize = True, updatemodel = True)
Initialize Data  CDK1 = 0,TP53 = 1,ERK_PP = 1,E2F1 = 1,CCNG1 =
  1,WIP1 = 0,CDKN1A = 1,ATM = 1,RB1 = 1,CASP9 = 0,PTEN = 1,CDK2 =
  0,BAX = 1,ARF = 1,Raf_P = 0,AKT_P = 1,MDM2 = 0,MDM4 = 1,BCL2 =
  0 
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File
  "/home/alokendra/Documents/Research_and_Knowledge_Platform/Research_Database/CHIC_Project/Model_Scripts/hybrid_systems_simulator/hss/interface/combined_run.py",
  line 32, in Solve
    solver.Readfile(filename = solver.tmpfile)
TypeError: Readfile() got an unexpected keyword argument 'filename'
>>> model = copy.deepcopy(boolmodel_orig)
>>> combined_run.Solve(model["instance"], reinitialize = True, updatemodel = False)
Initialize Data  CDK1 = 0,TP53 = 1,ERK_PP = 1,E2F1 = 1,CCNG1 =
1,WIP1 = 0,CDKN1A = 1,ATM = 1,RB1 = 1,CASP9 = 0,PTEN = 1,CDK2 =
0,BAX = 1,ARF = 1,Raf_P = 0,AKT_P = 1,MDM2 = 0,MDM4 = 1,BCL2 = 0 
```

### Solve

**Function Signature**

```
def Solve(solver, reinitialize = False, updatemodel = True)
```

**Description**

This is the main solver function which is just a wrapper for a
particular class of solver (ode or boolean). It calls the
appropriate methods of the solver class to read the initial
configuration, make modifications based on sweep data, solve the
model and collect data.

**Input Parameters**

`solver` This is the particular instance of a specific type of
solver ODE or boolean.

`reinitialize` (boolean) This is a flag that indicates whether
the model is being run for the first time or not. Accordingly it
reads the initial model file and initializes the main data
structure.

`updatemodel` (boolean) Another boolean flag that indicates
whether or not to retain the final state of the model to be used
for next set of runs.
