#!/usr/bin/env python
"""
Run hybrid model simulations with memory OFF (updatemodel=False) for a single
(patient, drug) condition and save Cell_Fates results for comparison with
existing memory-ON results.

Must be run with the nephro conda environment (Python 2 + boolean2):
    /jet/home/aramamur/.conda/envs/nephro/bin/python run_no_memory.py [PATIENT] [DRUG] [NUM_SEEDS]

PATIENT:   patient to run (default: 4L3YB6). Use 'Control' for the control arm.
DRUG:      drug condition (default: Control). One of the 8 lifer drug combos.
NUM_SEEDS: number of replicate seeds to run, capped to whatever Arguments/
           sweep data is available (default: 10).

Output files (written to hss/interface/):
    Cell_Fates_nomem_lifer_<patient>_<drug>.json
"""

import os, sys, json, glob, itertools, copy
import multiprocessing as mp

# --------------------------------------------------------------------------- #
# Path setup -- must run from project root                                    #
# --------------------------------------------------------------------------- #
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
IFACE_DIR   = os.path.join(SCRIPT_DIR, 'hss', 'interface')
os.chdir(IFACE_DIR)

for rel in ['.', '../solver', '../visualization', '../utils', '../../tests']:
    p = os.path.abspath(rel)
    if p not in sys.path:
        sys.path.insert(0, p)

import hybrid_run                          # uses global Run_Info
from hss.solver import sweep as sweepmod  # Generate_Sweeps

# --------------------------------------------------------------------------- #
# Configuration                                                                #
# --------------------------------------------------------------------------- #
PATIENT    = sys.argv[1] if len(sys.argv) > 1 else '4L3YB6'
DRUG       = sys.argv[2] if len(sys.argv) > 2 else 'Control'
NUM_SEEDS  = int(sys.argv[3]) if len(sys.argv) > 3 else 10

# Listed so build_args_from_run_info() can find a same-patient reference
# condition to borrow init states from.
ALL_DRUGS = [
    'Control', 'Actinomycin', 'Dox', 'Actinomycin_Dox',
    'Vincristine', 'Dox_Vincristine', 'Actinomycin_Vincristine',
    'Actinomycin_Dox_Vincristine',
]

TIME_STEPS = 20.0

# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def load_run_info(patient, drug):
    fname = 'Run_Info_lifer_%s_%s.json' % (patient, drug)
    if not os.path.exists(fname):
        return None
    with open(fname) as f:
        return json.load(f)


def existing_args_files(patient, drug):
    """Sorted list of Arguments_lifer_PATIENT_DRUG_N.json files."""
    pattern = 'Arguments_lifer_%s_%s_*.json' % (patient, drug)
    files = glob.glob(pattern)
    files = sorted(files,
                   key=lambda f: int(f.rsplit('_', 1)[-1].replace('.json', '')))
    return files


def build_args_from_run_info(patient, drug, ref_patient=None):
    """
    Generate argument list for a condition that lacks pre-built Arguments files.
    Borrows Unconstrained_Nodes and init_states from another condition of the
    same patient (first drug that has files).
    """
    run_info = load_run_info(patient, drug)
    if run_info is None:
        return None

    # Prefer a reference condition from the SAME patient (init states and
    # Unconstrained_Nodes are patient-specific). Only fall back to another
    # patient if this patient has no other condition with Arguments files.
    ref_files = []
    for d in ALL_DRUGS:
        if d == drug:
            continue
        ref_files = existing_args_files(patient, d)
        if ref_files:
            break
    if not ref_files and ref_patient:
        for d in ALL_DRUGS:
            ref_files = existing_args_files(ref_patient, d)
            if ref_files:
                break
    if not ref_files:
        print('  [warn] no reference args found for %s_%s' % (patient, drug))
        return None

    # Read unconstrained nodes and all init states from reference files
    unconstrained_nodes = None
    init_states_seen = {}  # egf_val -> list of init_state tuples
    for f in ref_files:
        with open(f) as fp:
            d = json.load(fp)
        args = d['args']
        if unconstrained_nodes is None:
            unconstrained_nodes = args[1]
        egf_val = args[3][0]['value']
        key = tuple(args[2])
        if egf_val not in init_states_seen:
            init_states_seen[egf_val] = []
        if key not in init_states_seen[egf_val]:
            init_states_seen[egf_val].append(key)

    # Build sweep space from run_info
    sweep_data  = run_info['sweeps']['chenode']
    sweep_space = sweepmod.Generate_Sweeps(sweep_data)

    args_list = []
    num = 0
    for sweep_elem in sweep_space:
        sweep_elem_list = list(sweep_elem)
        egf_val = sweep_elem_list[0]['value']
        # Use init states seen for this EGF level; fall back to first level
        candidates = init_states_seen.get(egf_val) or init_states_seen.values()[0]
        for init_state in candidates:
            args_list.append((
                num,
                unconstrained_nodes,
                list(init_state),
                sweep_elem_list,
                False,     # updatemodel = False  (memory OFF)
                0,         # atm_activation_state
            ))
            num += 1

    print('  generated %d args for %s_%s from Run_Info' % (len(args_list), patient, drug))
    return args_list


def _run_one(args_mod):
    """Top-level (picklable) worker: run one replicate, never raise."""
    try:
        return hybrid_run.Coupled_Loop(tuple(args_mod))
    except Exception as exc:
        return {'_error': '%s' % exc, '_num': args_mod[0]}


def run_condition_nomem(patient, drug, num_seeds):
    """Run up to num_seeds replicate simulations with memory OFF (in
    parallel) and return fate counts."""
    run_info = load_run_info(patient, drug)
    if run_info is None:
        print('  no Run_Info for %s_%s -- skip' % (patient, drug))
        return None

    # Make Run_Info available as the global that Coupled_Loop reads.
    # Must happen before the Pool is created so forked workers inherit it.
    hybrid_run.Run_Info = run_info

    # Get or generate the argument list
    args_files = existing_args_files(patient, drug)
    if args_files:
        args_list = []
        for f in args_files:
            with open(f) as fp:
                args_list.append(json.load(fp)['args'])
    else:
        args_list = build_args_from_run_info(patient, drug, ref_patient=patient)
        if args_list is None:
            return None

    args_list = args_list[:num_seeds]

    args_mods = []
    for args in args_list:
        args_mod = list(args)
        args_mod[4] = False  # memory OFF
        args_mods.append(args_mod)

    n_workers = min(mp.cpu_count(), len(args_mods))
    print('  launching %d runs across %d workers' % (len(args_mods), n_workers))
    pool = mp.Pool(n_workers)
    try:
        results = pool.map(_run_one, args_mods)
    finally:
        pool.close()
        pool.join()

    counts = {'cell_death': [], 'cell_growth': [], 'cell_senescence': []}
    n_ok = 0
    for result in results:
        if '_error' in result:
            print('  error in run %d: %s' % (result['_num'], result['_error']))
            continue
        for name, data in result.items():
            if isinstance(data, dict) and 'cell_fate_lookup' in data:
                for fate, cnt in data['cell_fate_lookup'].items():
                    counts[fate].append(cnt)
                n_ok += 1

    print('  completed %d / %d runs' % (n_ok, len(args_mods)))
    return counts


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
outfile = 'Cell_Fates_nomem_lifer_%s_%s.json' % (PATIENT, DRUG)

print('\nRunning memory-OFF: patient=%s  drug=%s  seeds=%d' % (PATIENT, DRUG, NUM_SEEDS))
counts = run_condition_nomem(PATIENT, DRUG, NUM_SEEDS)

if counts is None or not any(counts.values()):
    print('  no data collected -- skip')
else:
    total = float(sum(sum(v) for v in counts.values()))
    probs = {k: sum(v) / total for k, v in counts.items()} if total > 0 else {}

    out = {
        'Cell_Fates_Lookup': counts,
        'Cell_Fate_Probabilities_Lookup': probs,
    }
    with open(outfile, 'w') as f:
        json.dump(out, f)
    print('  saved %s   death=%.3f  growth=%.3f  sen=%.3f' % (
        outfile,
        probs.get('cell_death', 0),
        probs.get('cell_growth', 0),
        probs.get('cell_senescence', 0),
    ))

print('\nDone.')
