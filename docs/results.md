---
title: Calculation of Cell Fate Probability and CKR
author: Alok Ghosh
---

# Introduction

This script calculates the cell fate probabilities and cell kill
rates from the hybrid model output. This gets the data from each
sweep instance and calculates the average over different EGF
values and memory conditions and converts it into a format that
can be easily plotted.

# Cell Fate Calculation

The cell fates `cell_death`, `cell_growth` and `net_cell_growth`
will be extracted from different sweep instances, compiled and
then averaged over EGF and memory conditions. First we have to
get the data from specific files

## Initialization

This part will contain the hard coded cases and the
initialization for the main data structures. This will be
eventually moved to a separate configuration file or provided
through arguments.

```python
Patient = "Control"
Cases = ["Control", "Vincristine", "Dox", "Dox_Vincristine"]
```

The above variables `Patient` and `Cases` contains the particular
patient type (Control or cancer patient) and what drug
combinations were used. In this case we have a control group
(with base genetic expression) and all possible cases with the
chemotherapeutic drugs Dox and Vincristine.

```python
Cell_Fate_Patient_List = {}
```

This initializes the main dictionary `Cell_Fate_Patient_List`
which holds the cell fate data. This dictionary has the following
structure (shown for the case of control patient with no drug).

```json
{
    "Control_Control" : {
	    "cell_death" : []
	    "cell_growth" : []
	    "cell_senescence" : []
	    "net_cell_growth" : []
		}
}
```
It will have similar keys for all other drug combinations.

## Main Loop and data import

Next comes the main loop that imports the model and sweep data
from the files for specific cases

```python
for drug in Cases:
    Datadir = os.path.join("Archive", Patient + "_" + drug)

    Model_Data_File = "Model_Data_%s_%s.pickle" % (Patient, drug)
    Sweep_Data_File = "Sweepfile_%s_%s.json" % (Patient, drug)

    with open(os.path.join(Datadir, Model_Data_File)) as fp: Model_Data = pickle.load(fp)
    with open(os.path.join(Datadir, Sweep_Data_File)) as fp: Sweep_Data = json.load(fp)
```

After this we can call a function that will transform the sweep
data into an appropriate format

```python
Sweep_Info = Sweep_Average()
```
