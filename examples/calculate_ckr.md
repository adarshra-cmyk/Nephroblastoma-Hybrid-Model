# Calculate Cell Kill Rate

## Description

This script uses the hybrid solver module to calculate cell kill
rate for patients of nephroblastoma and lung cancer. It uses a
preprocessor to obtain the input data which consists of

- Patient miRNA/mRNA information
- Patient treatment information - name of drug and dosages
- Base configuration of signaling pathways
- Information on known interaction of pathways

It uses the following modules to obtain cell kill probabilities

1. `Drug_Targets` This looks up internal/external drug databases
   and returns information on how specific network node states
   (discrete or continuous) need to be altered
2. `Gene_Targets` This looks up internal/external genetic
   databases and returns information on how specific network node
   states need to be altered based on patient genetic information
3. `Runner` This module uses the genetic and drug dosage
   information and network configuration to determine how the
   individual solvers would run and interact. It also
   obtains user specific information such as main hypothesis under
   test or sensitivity analysis and system specific details (32/64 bit
   etc) and comes up with a simulation workflow
4. `Solver` These are individual solvers or wrappers around them
   for various models continuous and Boolean which obtains system
   state at future times for specific input
5. `Validator` This validates the main input to ensure this is
   consistent for individual models
6. `Cell_Kill_Ratio` This uses the individual model outputs and
   calculates the cell kill ratio based on the running scheme
7. `Sensitivity_Analysis` This calculates the sensitivity of the
   model combinations
8. `SRE` This calculates the sloppyness, robustness and
   evolvability of model combination
9. `Visualization` This module generates all types of
   visualization from time course plots, cell fate bar plots etc
