#!/usr/bin/env python
"""
Consensus run: all 8 drug conditions using the Control patient's Boolean
initial state (no miRNA suppression). Isolates the pure drug effect from
patient-specific personalization.

Usage:
    /jet/home/aramamur/.conda/envs/nephro/bin/python run_consensus.py [NUM_SEEDS]

Output (written to hss/interface/):
    Cell_Fates_nomem_lifer_Consensus_<drug>.json
"""

import os, sys, json, glob, copy
import multiprocessing as mp

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IFACE_DIR  = os.path.join(SCRIPT_DIR, 'hss', 'interface')
os.chdir(IFACE_DIR)

for rel in ['.', '../solver', '../visualization', '../utils', '../../tests']:
    p = os.path.abspath(rel)
    if p not in sys.path:
        sys.path.insert(0, p)

import hybrid_run
from hss.solver import sweep as sweepmod

NUM_SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 10

ALL_DRUGS = [
    'Control', 'Actinomycin', 'Dox', 'Actinomycin_Dox',
    'Vincristine', 'Dox_Vincristine', 'Actinomycin_Vincristine',
    'Actinomycin_Dox_Vincristine',
]


def load_run_info(drug):
    fname = 'Run_Info_lifer_Control_%s.json' % drug
    if not os.path.exists(fname):
        return None
    with open(fname) as f:
        return json.load(f)


def existing_args_files(drug):
    pattern = 'Arguments_lifer_Control_%s_*.json' % drug
    files = glob.glob(pattern)
    return sorted(files, key=lambda f: int(f.rsplit('_', 1)[-1].replace('.json', '')))


def build_args_from_run_info(drug):
    """Generate args for conditions without pre-built Arguments files,
    borrowing Unconstrained_Nodes from any Control condition that has them."""
    run_info = load_run_info(drug)
    if run_info is None:
        return None

    # Find any Control condition with pre-built args to borrow init states from
    ref_files = []
    for d in ALL_DRUGS:
        if d == drug:
            continue
        ref_files = existing_args_files(d)
        if ref_files:
            break

    if not ref_files:
        print('  [warn] no reference args found for Control_%s' % drug)
        return None

    unconstrained_nodes = None
    init_states_seen = {}
    for f in ref_files:
        with open(f) as fp:
            d_data = json.load(fp)
        args = d_data['args']
        if unconstrained_nodes is None:
            unconstrained_nodes = args[1]
        egf_val = args[3][0]['value']
        key = tuple(args[2])
        if egf_val not in init_states_seen:
            init_states_seen[egf_val] = []
        if key not in init_states_seen[egf_val]:
            init_states_seen[egf_val].append(key)

    sweep_data  = run_info['sweeps']['chenode']
    sweep_space = sweepmod.Generate_Sweeps(sweep_data)

    args_list = []
    num = 0
    for sweep_elem in sweep_space:
        sweep_elem_list = list(sweep_elem)
        egf_val = sweep_elem_list[0]['value']
        candidates = init_states_seen.get(egf_val) or list(init_states_seen.values())[0]
        for init_state in candidates:
            args_list.append((
                num,
                unconstrained_nodes,
                list(init_state),
                sweep_elem_list,
                False,  # memory OFF
                0,      # atm_activation_state
            ))
            num += 1

    print('  generated %d args for Consensus_%s from Run_Info' % (len(args_list), drug))
    return args_list


def _run_one(args_mod):
    try:
        return hybrid_run.Coupled_Loop(tuple(args_mod))
    except Exception as exc:
        return {'_error': '%s' % exc, '_num': args_mod[0]}


def run_consensus_drug(drug):
    run_info = load_run_info(drug)
    if run_info is None:
        print('  no Run_Info for Control_%s -- skip' % drug)
        return None

    hybrid_run.Run_Info = run_info

    args_files = existing_args_files(drug)
    if args_files:
        args_list = []
        for f in args_files:
            with open(f) as fp:
                args_list.append(json.load(fp)['args'])
    else:
        args_list = build_args_from_run_info(drug)
        if args_list is None:
            return None

    args_list = args_list[:NUM_SEEDS]

    args_mods = [list(a) for a in args_list]
    for a in args_mods:
        a[4] = False  # memory OFF

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
# Main
# --------------------------------------------------------------------------- #
print('\nConsensus run (no miRNA personalization) -- %d seeds per drug\n' % NUM_SEEDS)

summary = {}
for drug in ALL_DRUGS:
    print('Drug: %s' % drug)
    counts = run_consensus_drug(drug)
    if counts is None or not any(counts.values()):
        print('  no data -- skip\n')
        continue

    total = float(sum(sum(v) for v in counts.values()))
    probs = {k: sum(v) / total for k, v in counts.items()} if total > 0 else {}

    out = {
        'Cell_Fates_Lookup': counts,
        'Cell_Fate_Probabilities_Lookup': probs,
    }
    outfile = 'Cell_Fates_nomem_lifer_Consensus_%s.json' % drug
    with open(outfile, 'w') as f:
        json.dump(out, f)

    ncg = probs.get('cell_growth', 0) - probs.get('cell_death', 0)
    summary[drug] = ncg
    print('  saved %s   NCG=%.3f  (death=%.3f  growth=%.3f  sen=%.3f)\n' % (
        outfile, ncg,
        probs.get('cell_death', 0),
        probs.get('cell_growth', 0),
        probs.get('cell_senescence', 0),
    ))

print('\n=== Consensus NCG Summary ===')
for drug, ncg in sorted(summary.items(), key=lambda x: x[1]):
    bar = '#' * int(abs(ncg) * 20)
    sign = '-' if ncg < 0 else '+'
    print('  %-35s  NCG=%+.3f  %s%s' % (drug, ncg, sign, bar))

print('\nDone.')
