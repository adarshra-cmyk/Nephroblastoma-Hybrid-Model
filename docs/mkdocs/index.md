# Hybrid Systems Simulator 

## Overview

The hybrid simulator is a general framework for combining systems
models of various pathways of cancers such as EGFR driven
PI3K/AKT and Ras/MAPK, TP53 mediated DNA damage response pathways
which are important in cancers of kidney, lung and prostate. The
models can have both continuous or discrete time descriptions and
different time scales. This has the following features:

  - Easily run individual modules separately (without coupling)
and visualize the results
  - Connect modules one at a time or all of them and compare with
individual data
  - Perform global sensitivity, sloppyness analysis and other
validation checks on individual and whole models
  - Add effect of drugs and variations in tumor microenvironments.


## Organization

Based on these classes and requirements, our design should have
the following modules

### Input data and preprocessing

This module gets relevant input data such as network
configuration and rate constants, information about patient
specific genetic information and treatment conditions from
various sources and produces modified cps files or data matrices
that can be passed to individual solvers. More details can
be found in the [preprocessor](preprocessor.md) and the
<a href="preprocessor.m.html">API Docs</a>.

### Runners

These allow users to specify a simulation scheme mimicking a
specific clinical scenario and generates a workflow that allows
running the solvers on PBS based clusters like compbio. More
details can be found in the API documentations for <a
href="batch_setup.m.html">`batch_setup.py`</a> and <a
href="job_setup.m.html">`job_setup.py`</a> scripts.

### Solvers

These consists of ODE and boolean solvers that generates state
transition diagrams and time course data for various initial
configurations.

### Model Coupling

This part consists of the logic to be used to couple one or more
models by using user specified information about interfaces,
determine a running scheme for the solvers and manage information
exchange between them. More details can be found in the
[Hybrid Model](hybrid_run.md) section and the corresponding
<a href="hybrid_run.m.html">API documentation</a>.

### Viewers

These obtains the output from the model and obtains visualization
for specific sets of runs.

## Running Simulations

Running simulations will require us to follow the above
organization somewhat in the same order. We need to run the
preprocessing scripts, the run the batch scripts which use the
scripts that couple the models and solve them individually.

### Setting Up Virtual Environment

When running the simulation for the first time, it is needed to
setup a new virtual environment first and then installing the
necessary packages (listed in
<a href="../requirements.txt">requirements.txt</a> file. The following set
of commands can be used

```
$ virtualenv ./pyenv
$ echo "pyenv/" >> .gitignore
$ source ./pyenv/bin/activate
$ pip install -r requirements.txt
```

All the commands below should be run by activating the virtual
environment first using the above commands.

### Preprocessing

The main script to be run here is `hss/io/preprocessor.py`. The
main input file is `hss/interface/Run_Info.json`. For example
to perform the preprocessing for the patient with pseudo
anonymized id `5XIHQG` with the drug combinations Dox and
Vincristine one can use the following commands

```
$ cd hss/io
$ ./preprocessor.py -p 5XIHQG -d "Dox,Vincristine" ../interface/Run_Info.json
```

Currently only Dox and Vincristine are supported. Patient miRNA
files are available in the `mirna_data` folder.
More details can be found in the API documentation
in <a href="preprocessor.m.html">here</a>.

### Batch Setup

The main script that does this setup process
is the `Batch_Build()` function in
`hss/interface/batch_setup.py`. This script can be run in two 
modes. When run for the first time for a particular patient
and drug combination, the `-i` flag is to be used. For e.g. for
the patient `5XIHQG` with the drugs Dox and Vincristine one needs
to run the following commands

```
$ python batch_setup.py -i Run_Info_5XIHQG_Dox_Vincristine.json
```

This sets up the run for the patient 5XIHQG and the drug
combination Dox and Vincristine. This creates a file that
contains all the sweep conditions which will be used to setup the
runs, track them and collect data.

### Batch Run and Update

To run the jobs by submitting them to a PBS based cluster like
compbio the same script `batch_setup.py` is run but without the
`-i` flag like below

```
$ python batch_setup.py Run_Info_5XIHQG_Dox_Vincristine.json >> 5XIHQG_Dox_Vincristine.log
```

This command submits the individual sweeps as separate jobs and
stores information related to these jobs. This is done by the
`Batch_Run()` function in this script.

Then the second command can be run on regular intervals to update
the status of the runs. A simple <a
href="../hss/interface/Monitor_Jobs.sh">shell script</a> like
below can be setup for this purpose:

```bash
#!/bin/bash

source /mnt/io1/compbio/home/aghos/workdir/hybrid_systems_simulator/pyenv/bin/activate 

for i in $(seq $2)
do
    sleep $1
    date
    python batch_setup.py $3
done

deactivate
```

Note that to run the above shell script one MUST setup a virtual
environment called  `pyenv` (or something else, change the name
in the shell script accordingly. The above script must be
provided with three arguments. First one is the time interval (such
as `30m`) after which the script will be run. The second one is
the number of such intervals. The third one is the name of the
input json file which is passed to the script. So for the above
patient `5XIHQG` with Dox and Vincristine one can run the script
as below (after running the script separately with `-i` option
and without the `-i` flag to submit the runs).

```
nohup ./Monitor_Jobs.sh 30m 15 Run_Info_5XIHQG_Dox_Vincristine.json &>> 5XIHQG_Dox_Vincristine.log &
```

The above command will make sure that the script is run as a
process detached from the parent shell and the output is stored
in a log file which can be viewed later.

### Batch Data Collection

After all the runs are completed the same command as the
preceding section can be run to complete the data collection
which is done by `Batch_Collect()` function. For this the same
command as above is invoked

```
$ python batch_setup.py Run_Info_5XIHQG_Dox_Vincristine.json >> 5XIHQG_Dox_Vincristine.log
```

All the relevant data are stored in a separate folder which has
the same name as the sweep id.

## Post Processing

The main post processing script is `hss/visualization/results.py`
which gets the cell fate bar plots and the time courses for the
different sweep elements. This script is invoked in a similar
manner as the preprocessing script

```
$ python results.py -p 5XIHQG -d "Control,Dox,Vincristine"
```

If these options are not provided all of the cases are assumed as
Control and no drug. Typically it does not makes sense to run
this without at least two or more drug conditions as the
objective is to compare the cell fates in presence and absence of
the drug.
