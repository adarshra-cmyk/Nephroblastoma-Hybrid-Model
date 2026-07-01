# Nephroblastoma Hybrid Model

A hybrid ODE + Boolean network simulator for predicting patient-specific chemotherapy response in nephroblastoma (Wilms tumor, pediatric kidney cancer).

The model couples a continuous ErbB/EGFR signaling ODE (COPASI) with a discrete p53-mediated DNA damage Boolean network to compute per-patient cell fate probabilities (growth, death, senescence) under combinations of Actinomycin, Doxorubicin, and Vincristine.

## How it works

1. **ODE step** — Run ErbB/EGFR signaling model; discretize interface node concentrations into Boolean states
2. **Boolean step** — Use discretized ODE output as initial conditions for p53 Boolean network; determine cell fate
3. Repeat for 20 coupling steps; tally fate at each step
4. Patient miRNA expression profiles adjust Boolean initial states to personalize predictions

Net cell growth (NCG) is defined as `cell_growth% - cell_death%` per step, and is validated against actual pre/post-treatment tumor volumes.

## Repository structure

```
hss/                        Core simulator package
  solver/
    boolsolve.py            Boolean network solver (booleannet)
    odesolve.py             ODE solver (COPASI via subprocess)
    sweep.py                Parameter sweep utilities
  interface/
    hybrid_run.py           ODE-Boolean coupling logic
    extract_cell_fates.py   Collect cell fate outputs from simulation pickles
    submit_no_memory.py     Stateless (no state carry-forward) runs
  io/
    preprocessor.py         Patient miRNA -> personalized Boolean config
    drug.py                 Drug effect definitions
  utils/                    HPC job submission utilities (Bridges-2/SLURM)
  visualization/            Plotting helpers

generate_figures.py         Reproduce Figures 1-3 from Cell_Fates outputs
compare_memory_ncg.py       Compare NCG with memory ON vs OFF
run_consensus.py            Run all drug conditions with control patient Boolean init
run_no_memory.py            Run stateless simulations
setup_new_patients.py       Integrate new patient miRNA data
examples/                   Standalone usage examples
tests/                      Unit and integration tests
```

## Dependencies

- Python 3.x
- numpy, pandas, matplotlib, seaborn, scipy
- [booleannet](https://github.com/ialbert/booleannet) — Boolean network solver
- [COPASI](https://copasi.org/) (`CopasiSE` CLI) — ODE solver

Install Python dependencies:

```bash
conda env create -f nephro-conda.yml
conda activate nephro
```

## Running simulations

```bash
# Run all drug x patient combinations (parallelized over seeds)
python run_consensus.py

# Run stateless simulations
python run_no_memory.py

# Integrate new patient miRNA data and generate run configs
python setup_new_patients.py
```

Outputs are written to `hss/interface/Cell_Fates_lifer_<patient>_<drug>.json`.

## Reproducing figures

```bash
python generate_figures.py
```

Produces:
- **Figure 1** — Cell fate distributions (growth / death / senescence) per patient x drug
- **Figure 2** — Net cell growth probability across all drug combinations (strip plot)
- **Figure 2.5** — Hybrid model synergy vs. Bliss independence vs. additive sum
- **Figure 3** — Predicted net cell growth vs. actual net tumor volume change (validation)

## Patients

Five original patients (`4L3YB6`, `5XIHQG`, `6Z34IQ`, `ECCOAH`, and a drug-free `Control`) plus four additional patients with pre/post tumor volume data for Figure 3 validation.

Patient IDs are pseudonymized.
