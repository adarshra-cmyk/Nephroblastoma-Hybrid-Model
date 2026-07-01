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

### Input data

This module gets relevant input data such as network
configuration and rate constants, information about patient
specific genetic information and treatment conditions from
various sources and produces modified cps files or data matrices
that can be passed to individual solvers

### Runners

These allow users to specify a
simulation scheme mimicking a specific clinical scenario and
generates a workflow that allows running the solvers under in
specific orders

### Solvers

These consists of PDE, ODE and
boolean solvers that generates state transition diagrams and time
course data for various initial configurations.

### Model Coupling

This part consists of
the logic to be used to couple one or more models by using user
specified information about interfaces, determine a running
scheme for the solvers and manage information exchange between
them.

### Analyzers

These perform sensitivity,
sloppyness and robustness analysis on specific networks using the
solver modules and generate sensitivity eigenspectra or other
relevant information.

### Viewers

These obtains the output from
the model and obtains visualization for specific sets of runs

## Running Simulations

## Collecting Data

## Post Processing
