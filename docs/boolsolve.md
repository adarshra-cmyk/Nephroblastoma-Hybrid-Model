# Objective

This is the script containing classes for boolean solvers. The
purpose is to read a model in a json format and evolve the model
using the specified boolean rules.

## BoolNetSolver

This class uses booleannet module to evolve a boolean network and
find final states such as fixed point and cycles.

Methods

### Constructor

This constructor basically calls the constructor of the parent
class `BoolSolver` and hence does not need to be defined
separately here.

The parent class constructor initializes the input file name and
the parameters to be changed. It initializes the following
variables

`current_step` Indicates the current step number for the instance.
`num_runs` Indicates the number of runs of the model
`num_data` Indicates the number of times data has been extracted
from the model
`job_status` Indicates the status of a job.

### Initialize_Data

This first calls the corresponding method of the parent
class. 

`all_states` This method first creates a list for the list
`all_states` and the first element which it copies.

`data` This then updates the data in the instance with the keys
from the network and the first element as the initial state.

The subclass also obtains the `interaction_matrix` and generates
the `Rules`.

### Change_Parameters

This method performs the network parameter change using the
`parameter` attribute. It updates both `states` and the `network`
attribute. For the latter it locates the `initial_state` and
changes it.

### Solve

This uses standard booleannet model initialization and iteration
methods to evolve the model forward.

### Get_Data

This obtains the final state of the network and updates the
`states` with the final state and then it appends the states into
`data`.

State Changes During Self-Testing


