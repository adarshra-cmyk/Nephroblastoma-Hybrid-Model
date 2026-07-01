---
title: Coupled Run
header-includes:
    <link href="styles.css" rel="stylesheet"/>
---

## Objective

This script runs two or more ode and boolean instances together
using specific information about the interfaces.

## Functions

### Solve

Signature

```
def Solve(solver, reinitialize=False):
```

This function runs individual solver using a common set of
methods. Depending on whether the `reinitialize` flag is set
false or true it will read a new file and initialize the data. 

It then creates a temporary file and calls the method to change
the parameters. Then it writes a new file and calls the
solver. Finally it obtains the data and perfoms cleanup
operation. Then it gets the data for interface nodes.

### Main

The main section now contains separate code containing function
calls for individual ode,
boolean and coupled runs which are regulated by a hard coded flag
called `Run_Mode`. Same applies for plotting data. Ideally all of
this should be determined based on command line flags or from
configuration json files. In a class based
design this should be polymorphic in the sense that it will call
a single batch method which will be appropriate for the
particular type of run. The type of object we are dealing with
here is a Runtype (Ode, Boolean, Coupled, Demo etc). Depending on the
choice it should call appropriate methods.

There are also significant differences between the batch run for
ode, boolean and coupled mode. However the individual solver step
is similar.

The immediate modifications for the main section would be

- Move the hard coded variables to a separate json file
- Completely separate code for different batch runs and plots
- Remove other unnecessary code

### Batch\_Run\_Ode()

Signature

```
def Batch_Run_Ode():
```

This simply loops over the sweep space, instantiates a new
`OdeSolver` instance, solves the model and stores the modified
instance in a list and returns the whole list.

### Batch\_Run\_Bool()

Signature

```
def Batch_Run_Bool(modify_rules = False):
```

This takes an optional keyword parameter called `modify_rules`
which determines whether the booleannet rule file is to be
modified or not. If so it interactively asks for the name of the
modified file. Otherwise it calls the `Solve()` function first to
perform the initial run and then to run it in a loop.

Improvements- The main improvement opportunity here is the
`Solve()` function which was initially written to unify the
interfaces of the boolean and ode models. Because of the
significant differences between the way these two types of models
are run, they should be separated and instead made as part of two
different classes. Then the same `Solve()` method can be called.

We can also include the final state type determination (cycle or
fixed point) because we are actually iterating over all the
states. This can be much more simplified if we directly call the
underlying methods of the `booleannet` model object rather than
the wrapper `Solver()` function.


### Batch\_Run()

Signature

```
def Batch_Run(Parallel = False):
```

This is the main function to conduct a ode+bool coupled
run. Depending on whether we want to parallelize or not there are
two different ways to run it. Its basic functions are as
follows-

a) Determine the list of unconstrained nodes based on the initial
conditions and interface nodes.

b) Generate the overall sweep space by combining the sampled
initial state space with the sweep elements and with/without
memory.

c) Call the `Coupled_Loop()` function which conducts the actual
run of the models for one particular element of sweep space. 

d) Collect the results and determine the cell fate from the data

Improvements

This function is definitely doing too many things. We can easily
move the determination of unconstrained nodes upstream and the
determination of cell fates downstream in the post processing
section. Even the sweep space determination can be moved to a
separate function. The other option will be convert this to a
class with the `Coupled_Loop()` function.

Also we have to think which are the actual unconstrained
nodes. In the control case nothing but ATM satisfies the criteria
for the initial run.

### Coupled\_Loop()

Signature

```
def Coupled_Loop(args):
    """
    Runs the inner part of loop for batch run
    """
    num, Unconstrained_Nodes, init_state, sweep_elem, updatemodel = args
```

This function is just another level of modularization to enable
parallel and series runs. Its main tasks are as follows

a) Update the initial states of the unconstrained nodes
b) Instantiate two instances of ode and boolean solvers
c) Perform an initial and equilibration runs by calling
`Coupled_Run()` function
d) The remaining steps are just data collection for intermediate
steps, store cell fate values and print time information

Improvements-

a) The printing of state and time information should 
be made using decorators to remove hard coding.

b) The data collection process needs to be streamlined so that we
have minimum redundancies and are not storing unnecessary data.

### Coupled\_Run()

Signature

```
def Coupled_Run(oderun, boolrun, interface, reinitialize = False, updatemodel = True):
```

This is the main function that runs a single step of ode and
boolean model together. It operates based on two flags
`reinitialize` which specifies whether we are performing the
first run or not and `updatemodel` which specifies whether we
want to run with or without memory. For boolean model we will
always run with memory (for this and other reasons it may be
useful to separate the `Solve()` function). It gets the continuous
and discrete data from ode and boolean runs and converts them to
pass into the other model.

Improvement- This function needs to be generalized so that it can
deal with any number of ode and boolean instances. The
information about how to couple them should be in the
`Interface`. For this reason there needs to be a uniform
interface for calling the respective solvers.

The best way at this point is to define the `Solve()` function as
part of the individual ode and boolrun classes. This will be a
kind of wrapper over the regular `Solve()` method or an improved
version of it.
