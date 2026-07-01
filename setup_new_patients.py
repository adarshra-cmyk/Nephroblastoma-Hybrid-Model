#!/usr/bin/env python3
"""
setup_new_patients.py

Generates all necessary files to run the nephroblastoma hybrid model
for new patients from Pat_Mirna.json (extracted from
../extra_nephroblastoma_data.zip).

Active patients (have tumor volume data for validation):
  LAJDYMZBY4K262EJRR3V, KOLQXCKDRWLYVCATQAMF, M2Z4XCTXSR3NCW454E5E, XEON5Z
  (XEON5Z == XEON5ZV5NZIIKEAQHY4M in the volume spreadsheet)

Excluded (no tumor volume data):
  XP4HDLZRP5OGZ, 4FR5Z2DRG647WZ2TXVVF

For each active patient × drug condition (8 combos) × 16 seeds, creates:
  hss/io/mirna_data/miRNA_<PATIENT>.csv
  tests/p53_Boolean_<PATIENT>_<DRUG>.json
  hss/interface/Run_Info_lifer_<PATIENT>_<DRUG>.json
  hss/interface/Arguments_lifer_<PATIENT>_<DRUG>_<SEED>.json
  hss/interface/Jobfile_lifer_<PATIENT>_<DRUG>_<SEED>.sh

Run from the project root:
    python3 setup_new_patients.py [--dry-run] [--patient PATIENT]
"""

import os, sys, json, csv, copy, random, itertools, argparse

# --------------------------------------------------------------------------- #
# Paths                                                                        #
# --------------------------------------------------------------------------- #
PROJ   = os.path.dirname(os.path.abspath(__file__))
IFACE  = os.path.join(PROJ, 'hss', 'interface')
IO_DIR = os.path.join(PROJ, 'hss', 'io')
TESTS  = os.path.join(PROJ, 'tests')

# Patients excluded because they lack tumor volume data for validation
EXCLUDED_PATIENTS = {'XP4HDLZRP5OGZ', '4FR5Z2DRG647WZ2TXVVF'}

PAT_MIRNA_JSON = os.path.join(os.path.dirname(PROJ),
                               'extra_nephroblastoma_data',
                               'Pat_Mirna.json')
# Fallback: already extracted to scratchpad
PAT_MIRNA_FALLBACKS = [
    os.path.join(os.path.expanduser('~'), 'Pat_Mirna.json'),          # ~/Pat_Mirna.json
    os.path.join(os.path.expanduser('~'), 'extra_nephroblastoma_data',
                 'Lindsey-Kewei-WT projects', 'Patient Data from Alok_s resources',
                 'Pat_Mirna.json'),
    '/tmp/Pat_Mirna.json',
]

# --------------------------------------------------------------------------- #
# Drug configuration (derived from Run_Info_lifer.json and verified against   #
# existing p53_Boolean_<patient>_<drug>.json files)                           #
# --------------------------------------------------------------------------- #
# Hill function: Base = round(3 / ((KD/dosage)^coeff + 1))
# Dox:        KD=0.1, dosage=0.2, coeff=2  -> base=2
# Vincristine: KD=0,  dosage=0.2, coeff=0  -> base=2  (0^0 = 1 in Python)
# Actinomycin: KD=0.05,dosage=0.4,coeff=1  -> base=3
DRUG_NODES = {
    'Dox':        ['ATM', 'TP53', 'BAX', 'BCL2'],
    'Vincristine': ['CDK1'],
    'Actinomycin': ['ATM', 'TP53', 'BAX', 'BCL2'],
}
DRUG_BASE = {
    'Dox': 2,
    'Vincristine': 2,
    'Actinomycin': 3,
}
DRUG_COMBOS = {
    'Control':                  [],
    'Dox':                      ['Dox'],
    'Vincristine':              ['Vincristine'],
    'Actinomycin':              ['Actinomycin'],
    'Dox_Vincristine':          ['Dox', 'Vincristine'],
    'Actinomycin_Dox':         ['Actinomycin', 'Dox'],
    'Actinomycin_Vincristine':  ['Actinomycin', 'Vincristine'],
    'Actinomycin_Dox_Vincristine': ['Actinomycin', 'Dox', 'Vincristine'],
}

# --------------------------------------------------------------------------- #
# Boolean model constants                                                      #
# --------------------------------------------------------------------------- #
# Interface nodes from ODE → Bool (from Run_Info_lifer.json choibool interfaces)
INTERFACE_NODES = frozenset(['ERK_PP', 'AKT_P', 'Raf_P', 'PTEN'])

# Nodes always constrained by base p53_Boolean.json changes.states
BASE_FIXED_STATES = {'ATM': 0, 'CDK1': 1}

# Cell-fate indicator configuration (from preprocessor.py)
INDICATOR_NODES = {
    'G1toS': ['CDK2', 'CASP9'],
    'G2toM': ['BCL2'],
}
INDICATORS = {
    'G1toS': [
        [{'CDK2': 1, 'CASP9': 0}, 'cell_growth'],
        [{'CDK2': 0, 'CASP9': 1}, 'cell_death'],
        [{'CDK2': 1, 'CASP9': 1}, 'cell_growth'],
        [{'CDK2': 0, 'CASP9': 0}, 'cell_senescence'],
    ],
    'G2toM': [
        [{'BCL2': 0}, 'cell_death'],
        [{'BCL2': 1}, 'cell_growth'],
    ],
}

# EGF sweep values (same as in Run_Info_lifer.json sweeps.chenode.EGF.value)
EGF_VALUES = [1e-07, 1e-09]
N_INIT_STATES_PER_EGF = 8   # 8 init states × 2 EGF = 16 seeds total

# --------------------------------------------------------------------------- #
# SLURM job template                                                           #
# --------------------------------------------------------------------------- #
SLURM_TEMPLATE = """\
#!/bin/bash
#SBATCH --job-name={jobname}
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=adarshra@seas.upenn.edu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=12:00:00
#SBATCH --account=mcb200052p
#SBATCH --partition=RM-shared
#SBATCH -o {jobname}.out
#SBATCH -e {jobname}.err

set -e
cd $SLURM_SUBMIT_DIR
export PATH=/jet/home/aramamur/bin/Copasi/COPASI-4.34.251-Linux-64bit/bin:$PATH
PYTHON=/jet/home/aramamur/.conda/envs/nephro/bin/python
echo "Job {jobname} started"
startime=$(date +%s)
$PYTHON hybrid_run.py {argfile} {modelfile}
endtime=$(date +%s)
runtime=$(( $endtime - $startime ))
date -d@$runtime -u +%H:%M:%S > {jobname}.time
echo "Job {jobname} ended"
"""

# --------------------------------------------------------------------------- #
# Load static reference data                                                   #
# --------------------------------------------------------------------------- #

def load_static_data():
    """Load base models and COPASI species data."""
    with open(os.path.join(TESTS, 'p53_Boolean.json')) as f:
        base_bool = json.load(f)
    with open(os.path.join(IFACE, 'Run_Info_lifer.json')) as f:
        base_run_info = json.load(f)
    with open(os.path.join(IO_DIR, 'Network_Species_Temp.json')) as f:
        ode_network = json.load(f)   # UPPERCASE_GENE -> [species_name, compartment]
    with open(os.path.join(IO_DIR, 'Network_Species_Temp_Values.json')) as f:
        species_values = json.load(f)  # 'species-compartment' -> value
    return base_bool, base_run_info, ode_network, species_values


def load_mirtarbase():
    """Build miRNA -> set(target_gene) mapping from miRTarBase CSV."""
    mirtarfile = os.path.join(IO_DIR, 'hsa_MTI.csv')
    mirna_to_targets = {}
    with open(mirtarfile) as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = row['miRNA']
            t = row['Target Gene']
            mirna_to_targets.setdefault(m, set()).add(t)
    return mirna_to_targets


def load_pat_mirna(json_path):
    """Load Pat_Mirna.json. Returns (patient_ids, mirna_names, expression_dict)."""
    with open(json_path) as f:
        data = json.load(f)
    mirna_names = data['mirna']
    patients = {k: v for k, v in data.items() if k != 'mirna'}
    return patients, mirna_names

# --------------------------------------------------------------------------- #
# miRNA preprocessing                                                          #
# --------------------------------------------------------------------------- #

def top_mirna(patient_id, mirna_names, patient_expr, top=30):
    """Return list of (mirna, expression) tuples for the top N expressed miRNAs."""
    pairs = list(zip(mirna_names, patient_expr))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:top]


def mirna_targets_for_patient(top_mirnas, mirna_to_targets):
    """Return set of all target genes for the given top miRNAs."""
    targets = set()
    for mirna, _ in top_mirnas:
        targets |= mirna_to_targets.get(mirna, set())
    return targets


def bool_restricted_nodes(all_targets, all_bool_nodes):
    """Intersect miRNA targets with Boolean network nodes."""
    return sorted(all_targets & all_bool_nodes)


def ode_restricted_entries(all_targets, ode_network, species_values, skip_genes=None):
    """
    Build list of ODE initialize entries for miRNA-targeted COPASI species.
    Sets each species to 60 % of its initial value.
    skip_genes: uppercase gene names to skip (e.g. EGF — controlled by sweep).
    """
    skip_genes = set(skip_genes or ['EGF'])
    entries = []
    target_upper = {t.upper() for t in all_targets}
    for gene_upper, (species, compartment) in ode_network.items():
        if gene_upper in skip_genes:
            continue
        if gene_upper not in target_upper:
            continue
        key = '%s-%s' % (species, compartment)
        raw_val = float(species_values.get(key, 0))
        value = 0.6 * round(raw_val, 3)
        entries.append({
            'Paramtype': 'Initial Species Values',
            'substitute': {
                'compartment': compartment,
                'species': species,
            },
            'value': value,
        })
    return entries

# --------------------------------------------------------------------------- #
# File generators                                                              #
# --------------------------------------------------------------------------- #

def write_mirna_csv(patient_id, mirna_names, patient_expr, dry_run=False):
    """Write hss/io/mirna_data/miRNA_<patient>.csv."""
    outpath = os.path.join(IO_DIR, 'mirna_data', 'miRNA_%s.csv' % patient_id)
    if not dry_run:
        with open(outpath, 'w') as f:
            for mirna, val in zip(mirna_names, patient_expr):
                f.write('%s\t%s\n' % (mirna, val))
    print('  CSV: %s' % outpath)
    return outpath


def write_bool_model(patient_id, drug_combo, mirna_bool_restricted,
                     base_bool, dry_run=False):
    """
    Write tests/p53_Boolean_<patient>_<drug>.json.

    - Set miRNA-restricted nodes to state=0 in changes.states
    - Set drug-restricted nodes to state=1 (drug overrides miRNA for same nodes)
    - Set ATM/ARF base if any drug is active
    """
    model = copy.deepcopy(base_bool)

    # Start fresh changes (do NOT inherit base changes in the output file;
    # batch_setup.py reads the base p53_Boolean.json separately for base_changes)
    boolean_states = {}
    for node in mirna_bool_restricted:
        boolean_states[node] = 0

    active_drugs = DRUG_COMBOS[drug_combo]
    drug_node_set = set()
    atm_base = -1   # original
    arf_base = -1   # original

    if active_drugs:
        atm_base = max(DRUG_BASE[d] for d in active_drugs)
        arf_base = 0
        for d in active_drugs:
            for node in DRUG_NODES[d]:
                drug_node_set.add(node)
                boolean_states[node] = 1   # drug overrides miRNA

    model['changes'] = {'states': boolean_states, 'bases': {}}
    model['cell_states'] = INDICATORS
    model['indicator_nodes'] = INDICATOR_NODES

    if atm_base != -1:
        model['network']['ATM']['base'] = atm_base
    if arf_base != -1:
        model['network']['ARF']['base'] = arf_base

    fname = 'p53_Boolean_%s_%s.json' % (patient_id, drug_combo)
    outpath = os.path.join(TESTS, fname)
    if not dry_run:
        with open(outpath, 'w') as f:
            json.dump(model, f, indent=4)
    print('  Bool model: %s' % outpath)
    return outpath, boolean_states, drug_node_set


def write_run_info(patient_id, drug_combo, bool_modfile, mirna_bool_restricted,
                   drug_node_set, ode_init_entries, base_run_info, dry_run=False):
    """
    Write hss/interface/Run_Info_lifer_<patient>_<drug>.json.
    """
    ri = copy.deepcopy(base_run_info)
    run_id = 'lifer_%s_%s' % (patient_id, drug_combo)
    ri['run_id'] = run_id

    # Modfile points to the patient+drug-specific Boolean model
    # Path is relative to hss/interface/ (where hybrid_run.py runs)
    rel_modfile = '../../tests/%s' % os.path.basename(bool_modfile)
    ri['models']['choibool']['modfile'] = rel_modfile

    # Restricted nodes = miRNA-restricted + drug-restricted
    restricted = sorted(set(mirna_bool_restricted) | drug_node_set)
    ri['models']['choibool']['Restricted_Nodes'] = restricted

    # ODE initialize: keep base EGF entry, add miRNA ODE changes
    base_ode_init = copy.deepcopy(
        [e for e in base_run_info['models']['chenode']['initialize']]
    )
    ri['models']['chenode']['initialize'] = base_ode_init + ode_init_entries

    # Set drug status flags
    active_drugs = DRUG_COMBOS[drug_combo]
    for d in ri.get('drug', {}):
        ri['drug'][d]['status'] = 'on' if d in active_drugs else 'off'

    fname = 'Run_Info_lifer_%s_%s.json' % (patient_id, drug_combo)
    outpath = os.path.join(IFACE, fname)
    if not dry_run:
        with open(outpath, 'w') as f:
            json.dump(ri, f, indent=4)
    print('  Run_Info: %s' % outpath)
    return outpath


def compute_unconstrained_nodes(all_bool_nodes, mirna_bool_restricted, drug_node_set):
    """
    Compute unconstrained Boolean nodes for Arguments files.

    Constrained = interface_nodes + base_fixed_states + miRNA_restricted + drug_nodes
    batch_setup.py reads the BASE p53_Boolean.json (not the modfile) to get
    base_fixed_states, so CDK1/ATM are always constrained.
    """
    constrained = (INTERFACE_NODES
                   | set(BASE_FIXED_STATES.keys())
                   | set(mirna_bool_restricted)
                   | drug_node_set)
    unconstrained = sorted(all_bool_nodes - constrained)
    return unconstrained


def sample_init_states(unconstrained_nodes, n=N_INIT_STATES_PER_EGF, rng_seed=None):
    """
    Sample n random binary initial states for unconstrained nodes.
    Uses 2^SWEEP_LIMIT = 8 samples from the full state space (as in batch_setup.py).
    """
    space = list(itertools.product([0, 1], repeat=len(unconstrained_nodes)))
    if rng_seed is not None:
        random.seed(rng_seed)
    n_sample = min(n, len(space))
    return [list(s) for s in random.sample(space, n_sample)]


def write_arguments_files(patient_id, drug_combo, run_info_path,
                          unconstrained_nodes, init_states, dry_run=False):
    """
    Write 16 Arguments JSON files (8 init states × 2 EGF levels).
    Seeds 0-7: EGF=1e-07, Seeds 8-15: EGF=1e-09.
    """
    run_info_fname = os.path.basename(run_info_path)
    seed = 0
    written = []
    for egf_val in EGF_VALUES:
        sweep_elem = [{
            'Paramtype': 'Initial Species Values',
            'value': egf_val,
            'substitute': {'compartment': 'medium', 'species': 'EGF'},
        }]
        for init_state in init_states:
            sweep_id = 'lifer_%s_%s_%d' % (patient_id, drug_combo, seed)
            args_data = {
                'sweep_id': sweep_id,
                'args': [
                    seed,
                    unconstrained_nodes,
                    init_state,
                    sweep_elem,
                    True,   # updatemodel (memory ON)
                    0,      # atm_activation_state
                ],
            }
            fname = 'Arguments_lifer_%s_%s_%d.json' % (patient_id, drug_combo, seed)
            outpath = os.path.join(IFACE, fname)
            if not dry_run:
                with open(outpath, 'w') as f:
                    json.dump(args_data, f, indent=4)
            written.append(outpath)
            seed += 1
    print('  Arguments: %d files (seeds 0-%d)' % (len(written), seed - 1))
    return written


def write_jobfiles(patient_id, drug_combo, args_files, run_info_path, dry_run=False):
    """Write one SLURM Jobfile per Arguments file."""
    run_info_fname = os.path.basename(run_info_path)
    written = []
    for args_path in args_files:
        args_fname = os.path.basename(args_path)
        # Seed is the last integer in the filename
        seed = int(args_fname.replace('.json', '').rsplit('_', 1)[-1])
        jobname = 'lifer_%s_%s_%d' % (patient_id, drug_combo, seed)
        script = SLURM_TEMPLATE.format(
            jobname=jobname,
            argfile=args_fname,
            modelfile=run_info_fname,
        )
        fname = 'Jobfile_%s.sh' % jobname
        outpath = os.path.join(IFACE, fname)
        if not dry_run:
            with open(outpath, 'w') as f:
                f.write(script)
        written.append(outpath)
    print('  Jobfiles:  %d files' % len(written))
    return written

# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #

def find_pat_mirna():
    """Locate Pat_Mirna.json, searching several candidate paths."""
    candidates = [PAT_MIRNA_JSON] + PAT_MIRNA_FALLBACKS
    for path in candidates:
        if os.path.isfile(path):
            return path
    # Also check scratchpad
    import glob
    found = glob.glob('/tmp/**/Pat_Mirna.json', recursive=True)
    if found:
        return found[0]
    raise FileNotFoundError(
        'Pat_Mirna.json not found. Expected it at:\n  %s\n'
        'Extract it from extra_nephroblastoma_data.zip first.' % PAT_MIRNA_JSON
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                        help='Print what would be generated without writing files')
    parser.add_argument('--patient', metavar='ID',
                        help='Only process this patient ID')
    parser.add_argument('--pat-mirna', metavar='PATH',
                        help='Override path to Pat_Mirna.json')
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        print('[DRY RUN — no files will be written]\n')

    # Locate input data
    pat_mirna_path = args.pat_mirna or find_pat_mirna()
    print('Loading patient miRNA data from: %s' % pat_mirna_path)
    patients_expr, mirna_names = load_pat_mirna(pat_mirna_path)

    print('Loading reference models and databases...')
    base_bool, base_run_info, ode_network, species_values = load_static_data()
    mirna_to_targets = load_mirtarbase()
    all_bool_nodes = set(base_bool['network'].keys())

    patient_list = sorted(k for k in patients_expr.keys()
                          if k not in EXCLUDED_PATIENTS)
    if args.patient:
        if args.patient not in patient_list:
            print('ERROR: patient %r not found. Available: %s' %
                  (args.patient, patient_list))
            sys.exit(1)
        patient_list = [args.patient]

    drug_list = list(DRUG_COMBOS.keys())
    total = len(patient_list) * len(drug_list) * (1 + N_INIT_STATES_PER_EGF * len(EGF_VALUES))
    print('Generating files for %d patient(s) × %d drug conditions ...\n' %
          (len(patient_list), len(drug_list)))

    for patient_id in patient_list:
        print('=== Patient: %s ===' % patient_id)
        patient_expr = patients_expr[patient_id]

        # --- miRNA CSV ---
        write_mirna_csv(patient_id, mirna_names, patient_expr, dry_run=dry_run)

        # --- Compute patient-level miRNA restriction (same across all drugs) ---
        top_mirnas = top_mirna(patient_id, mirna_names, patient_expr, top=30)
        all_targets = mirna_targets_for_patient(top_mirnas, mirna_to_targets)
        mirna_bool_restricted = bool_restricted_nodes(all_targets, all_bool_nodes)
        ode_entries = ode_restricted_entries(all_targets, ode_network, species_values)

        print('  miRNA-restricted Boolean nodes: %s' % mirna_bool_restricted)
        print('  ODE init changes: %d entries' % len(ode_entries))

        # --- Per drug condition ---
        for drug_combo in drug_list:
            print('\n  -- Drug: %s --' % drug_combo)

            # Boolean model
            bool_modfile, boolean_states, drug_node_set = write_bool_model(
                patient_id, drug_combo, mirna_bool_restricted, base_bool,
                dry_run=dry_run,
            )

            # Run_Info
            run_info_path = write_run_info(
                patient_id, drug_combo, bool_modfile,
                mirna_bool_restricted, drug_node_set, ode_entries,
                base_run_info, dry_run=dry_run,
            )

            # Arguments + Jobfiles
            unconstrained = compute_unconstrained_nodes(
                all_bool_nodes, mirna_bool_restricted, drug_node_set)
            print('  Unconstrained nodes (%d): %s' % (len(unconstrained), unconstrained))

            # Use deterministic seed based on patient+drug for reproducibility
            rng_seed = abs(hash(patient_id + '_' + drug_combo)) % (2 ** 32)
            init_states = sample_init_states(unconstrained, N_INIT_STATES_PER_EGF,
                                             rng_seed=rng_seed)

            args_files = write_arguments_files(
                patient_id, drug_combo, run_info_path,
                unconstrained, init_states, dry_run=dry_run,
            )
            write_jobfiles(patient_id, drug_combo, args_files, run_info_path,
                           dry_run=dry_run)

        print()

    total_args = len(patient_list) * len(drug_list) * len(EGF_VALUES) * N_INIT_STATES_PER_EGF
    total_jobs = total_args
    print('\nDone.')
    print('  %d Arguments files' % total_args)
    print('  %d Jobfiles' % total_jobs)
    print()
    if not dry_run:
        print('To submit all new jobs, cd to hss/interface/ and run:')
        for patient_id in patient_list:
            for drug_combo in drug_list:
                for seed in range(len(EGF_VALUES) * N_INIT_STATES_PER_EGF):
                    print('  sbatch Jobfile_lifer_%s_%s_%d.sh' %
                          (patient_id, drug_combo, seed))
        print()
        print('Or use a loop:')
        print('  for f in Jobfile_lifer_%s_*.sh; do sbatch "$f"; done' %
              (patient_list[0] if len(patient_list) == 1 else '{PATIENT}'))


if __name__ == '__main__':
    main()
