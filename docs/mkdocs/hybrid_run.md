---
title: Hybrid Run
header-includes:
    <link href="styles.css" rel="stylesheet"/>
---

# Objective

This script runs the different component models of hybrid
framework for a particular sweep element.This needs a json file
containing the arguments to the function `Coupled_Loop()` which
specifies the sweep elements.

# Data

## Input Data

## Output Data

## Functions/Classes

### Coupled_Loop

**Function Signature**

```
def Coupled_Loop(args):
```

**Summary**

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
specification read in the main section. It gets the running
sequence of the models, number of steps and other model-specific
information.

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

**Description**

The first step here is to unpack the arguments received from the
external file into the local variables for the simulation number,
unconstrained nodes, initial states for the unconstrained nodes,
elements of the sweeps and whether or not to update the model.

```python
num, Unconstrained_Nodes, init_state, sweep_elem, updatemodel = args
model_data = {}
cell_fate = { "cell_death" : 0, "cell_growth" : 0, "cell_senescence" : 0 }
model_instance = []
```

Then it loops over the models in the specified sequence and
instantiates corresponding classes. For the ode model it calls
the `odesolve.OdeSolver` class which takes the name of the copasi
file, particular element of sweep containing nodes which are to
be changed and a model conversion factor.

It checks and makes sure that the species in the set of initial
conditions are not the same as that in the sweep elements by
looping through and checking the name of the corresponding
species. 

```python
for modelem in Run_Info["model_runs"]:
	model = copy.deepcopy(Run_Info["models"][modelem])
	if model["type"] == "ode":
		oderun = odesolve.OdeSolver(model["file"], sweep_elem, conv = model["conv"])
		for initelem in model["initialize"]:
			if initelem["substitute"]["species"] != sweep_elem[0]["substitute"]["species"]:
				oderun.parameter.append(initelem)
		model["instance"] = oderun
		model_instance.append(model)
```

Next for the boolean model the name of the file is used to
temporarily load the model json file. The corresponding initial
states from the arguments are then added in the "changes"
key. Then it instantiates a new model of type
`boolsolve.BoolNetSolver` with the name of the model file and the
changes that are to be made initially. Then it updates the
instance in the main list.

```python
if model["type"] == "boolean":
	with open(model["file"]) as fp: boolmodel = json.load(fp)
	boolmodel["changes"]["states"] = dict(zip(Unconstrained_Nodes, init_state))
	boolrun = boolsolve.BoolNetSolver(model["file"], boolmodel["changes"])
	model["instance"] = boolrun
	model_instance.append(model)
```

After this we call the `Coupled_Run()` function for the first
time to perform the initial runs for each model. At this stage
the value of `reinitialize` is set to True and `updatemodel` is
set based on the arguments. So for with memory case this will be
False and without memory case it will be True.

```python
Coupled_Run(model_instance, Run_Info["models"], Run_Info["model_runs"], reinitialize = True, updatemodel = updatemodel)
```

After the initial run this runs the models over specified number
of steps by setting `reinitialize` to False and again
`updatemodel` depending on memory. It collects data after
specified number of states to store state information. It also
calculates corresponding cell fates and stores them in a
dictionary.

```python
for step in range(Run_Info["steps"]):
	Coupled_Run(model_instance, Run_Info["models"], Run_Info["model_runs"], reinitialize = False, updatemodel = updatemodel)

	if step % 5 == 0:
		with open("Sim_Data_%s_%d_%d.pickle" % (Run_Info["run_id"],num,step), "wb") as fp: pickle.dump(
				{"odedata" : oderun.data,
					"booldata" : boolrun.data,
					"odemodel" : oderun.xmlstring,
					"boolmodel" : boolrun.network,
					"rules" : boolrun.Rules
				}, fp)
	cell_fate_step = Cell_Fate(boolrun, boolmodel["indicator"], default_state = "cell_senescence")
	cell_fate[cell_fate_step] += 1
```

At the end of the loop it collects data for each model and stores
them in a dictionary which is returned.

```python
for name, model in zip(Run_Info["model_runs"], model_instance):
	model_data[name] = {}
	model_data[name]["data"] = model["instance"].data
	model_data[name]["parameter"] = model["instance"].parameter
	if model["type"] == "boolean":
		model_data[name]["rules"] = model["instance"].Rules
		model_data[name]["cell_fate"] = cell_fate
	else:
		model_data[name]["interface_parameter"] = model["instance"].interface_parameter
```

Finally the dictionary `model_data` is returned to the caller.

### Coupled Run

**Function Signature**

```
def Coupled_Run(model_instances, models, model_runs, reinitialize = False, updatemodel = True):
```

**Summary**

This is the main function that runs a combination of models in
the hybrid framework together for a single step. It receives a
list of individual model instances and uses appropriate method
calls to initialize and run the models.

**Input Parameters**

`model_instances` (list) A list of model instances which were
initialized in the `Coupled_Loop()` function.

`models` (dict) Dictionary of the individual models containing
specific information.

`model_runs` (list) List of model names which specifies the order
in which they are to be run.

`reinitialize` (bool) A boolean value that specifies whether the
particular run is initialization or equilibration

`updatemodel` (bool) A boolean indicating whether the models are
to be run with or without memory.

**Output Parameters**

`None` The model directly changes the state of the provided model
instances.

**Local Parameters**

`discrete_data` (dict) Dictionary containing the discrete states
of the interface nodes.

`Interface_Data` (dict) Dictionary that contains interface node
information for the models which are needed for proper
conversion. 


**Global Parameters**

**Called Functions**

`Odesolve()` Calls the ode solver if one of the provided models
is an ODE

`Boolsolve()` Calls the boolean solver is one of the provided
model is boolean.

**Called by Functions**

`Coupled_Loop()` 

**Description**

First it initializes the variables used for storing the peak
concentrations, continuous, discrete and interface information
that are to be passed from model to model

```python
Peak_Conc = {}
continuous_data = {}
discrete_data = {}
Interface_Data = { key : models[key]["interfaces"] for key in model_runs }
```

Next the interface nodes which are in the following form are
converted into tuples along with node status.

```python
for key, value in Interface_Data.items():
	for ii, elem in enumerate(value):
		Interface_Data[key][ii]["nodes"] = dict(zip(map(tuple,elem["nodes"]), [0]*len(elem["nodes"])))
```

Next we loop over the models and depending on whether we are
running an ode model or boolean perform different actions. We
have two functions that perform the necessary steps depending on
whether the model is ODE or boolean.

```python
for name, model in zip(model_runs, model_instances):
	if model["type"] == "ode":
	    Odesolve(name, model, Interface_Data)
	elif model["type"] == "boolean":
	    Boolsolve(name, model, Interface_Data)
	else:
	    raise Exception("Model type %s is not implemented" % model["type"])
```

In the above code depending on whether the model is ode or
boolean, an appropriate solver is called. An exception is raised
if the model type does not match "ode" or "boolean".

**Example Run**

An example run showing the form of input and output data.

### Odesolve

**Function Signature**

```
def Odesolve(name, model, Interface_Data, reinitialize, updatemodel):
```

**Summary**

This function runs the appropriate methods for the ODE solver and
changes the model and interface data by getting the peak
concentrations.

**Input Parameters**

`name` (string) Name of the model

`model` (odesolve.OdeSolver) The ode model instance which is t be
solved.

`Interface_Data` (dict) A dictionary containing the interface
nodes and the discrete and continuous values.

`reinitialize` (bool) A boolean flag indicating whether the model
needs to be initialized before performing the run.

`updatemodel` (bool) A boolean flag indicating whether the model
is to be updated with the data from previous state.

**Output Parameters**

None

**Local Parameters**

`Peak_Conc` (dict) A dictionary containing the peak values of the
interface species in the specified solver duration.

`continuous_data` (dict) A dictionary containing the continuous
concentration of the species.

`compartments` (dict) Dictionary containing the compartments of
the individual species.

**Global Parameters**

Parameters which are shared from the calling function or the
global namespace.

**Called Functions**

`Interface()` Function that updates the status of the interface
nodes.

`Continuous()` Function that converts the discrete node status
into continuous.

**Called by Functions**

`Coupled_Run()` Called from within `Coupled_Run()` function.

**Description**

This function receives an ODE instance and solves the model. It
then updates the interface nodes and uses the peak concentrations
to convert the discrete node status into continuous.

First we initialize the key variables involved

```python
continuous_data = {}
Peak_Conc = {}
compartments = { key : value for key, value in model["interfaces"][0]["nodes"] }
```

Then we run the solver and update the interface
information. First we will call the solver methods and update the
data 

```python
if reinitialize:
	model["instance"].Readfile()
	model["instance"].Initialize_Data()
model["instance"].Createtempfile()
model["instance"].Change_Parameters()
model["instance"].Writefile()
model["instance"].Solve()
model["instance"].Get_Data()
if updatemodel:
	model["instance"].Readfile(filename = model["instance"].tmpfile)
model["instance"].Cleanup()
```

After this depending on whether we are doing an initial run or
not we will reset the parameters if we don't need to update the
parameters

```python
if reinitialize and updatemodel:
	model["instance"].parameter = []
```

Then we will update the interface nodes using the interface
specific information and get the peak concentration

```python
Interface(model["instance"], Interface_Data[name])
for elem in Interface_Data[name]:
	Peak_Conc.update({ key : max(value) for key, value in elem["nodes"].items() })
```

If we are not performing an initial run we need to convert the
discrete data obtained from previous boolean run into continuous

```python
if not reinitialize:
	continuous_data = Continuous(Interface_Data[Interface_Data[name][0]["other"]], Peak_Conc)
```

Finally we can use the continuous data to update the
corresponding value of the interface nodes. If this is not an
initial run then `continuous_data` would be empty so the loop
will not run.

```python
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
```

**Example Run**

An example run showing the form of input and output data.

### Boolsolve

**Function Signature**

```
def Boolsolve(name, model, Interface_Data, reinitialize, updatemodel):
```

**Summary**

This function runs the boolean model for a single time
step. Before running the boolean solver it gets the status of the
discrete nodes and uses them to initialize the model.

**Input Parameters**

`name` (`str`) Name of the model

`model` (`odesolve.OdeSolver`) The ode model instance which is to be
solved.

`Interface_Data` (`dict`) A dictionary containing the interface
nodes and the discrete and continuous values.

`reinitialize` (`bool`) A boolean flag indicating whether the model
needs to be initialized before evolving to the next step.

`updatemodel` (`bool`) A boolean flag indicating whether the model
is to be updated with the data from previous state.

**Output Parameters**

None

**Local Parameters**

`discrete_data` (dict) A dictionary containing the discrete node
states of the boolean.

**Global Parameters**

**Called Functions**

`Discretize()` Calls the function to convert continuous node
states into discrete

`Interface()` Function that updates the status of the interface
nodes.

**Called by Functions**

`Coupled_Run()` Called from within `Coupled_Run()` function.

**Description**

First the function initializes a dictionary to contain the
boolean node status. It then loops over the list of models with
which the boolean model shares an interface and gets the list of
discrete nodes whose status is updated.

```python
discrete_data = {}
for omodel in Interface_Data[name]:
	oname = omodel["other"]
	discrete_data.update(Discretize(Interface_Data[oname]))
```

Next if we are running the model first time or if the model is not
to be updated then we will add the interface nodes to set of
initial nodes to be changed. Otherwise we will overwrite so that
the initial nodes are removed and only the interface nodes remain.

```python
if reinitialize or (not updatemodel):
	model["instance"].parameter["states"].update(discrete_data)
else:
	model["instance"].parameter["states"] = discrete_data
```

Then we will call the appropriate solver methods for the boolean
model.

```python
if reinitialize:
	model["instance"].Readfile()
	model["instance"].Initialize_Data()
model["instance"].Createtempfile()
model["instance"].Change_Parameters()
model["instance"].Writefile()
model["instance"].Solve()
model["instance"].Get_Data()
model["instance"].Cleanup()
```

Finally we will update the interface nodes

```python
Interface(model["instance"], Interface_Data[name])
```

**Example Run**

An example run showing the form of input and output data.
