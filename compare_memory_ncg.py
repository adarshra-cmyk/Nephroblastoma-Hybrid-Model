"""
Compare Net Cell Growth (NCG) with memory ON vs OFF for Control and one
treatment patient across all available drug combinations.

Memory ON  = existing Cell_Fates_lifer_*.json  (updatemodel=True)
Memory OFF = Cell_Fates_nomem_lifer_*.json      (updatemodel=False, from run_no_memory.py)

Usage (from nephroblastoma_hybrid_model/):
    module load anaconda3
    python3 compare_memory_ncg.py [PATIENT]

PATIENT: optional second patient (default: 4L3YB6).
"""

import os, sys, json, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

# --------------------------------------------------------------------------- #
# Config                                                                       #
# --------------------------------------------------------------------------- #
TREATMENT_PATIENT = sys.argv[1] if len(sys.argv) > 1 else '4L3YB6'
PATIENTS          = ['Control', TREATMENT_PATIENT]

DRUGS = [
    'Control', 'Actinomycin', 'Dox', 'Actinomycin_Dox',
    'Vincristine', 'Dox_Vincristine', 'Actinomycin_Vincristine',
    'Actinomycin_Dox_Vincristine',
]
CHEMO      = ['Actinomycin', 'Dox', 'Vincristine']
TIME_STEPS = 20.0
WDIR       = 'hss/interface'

# --------------------------------------------------------------------------- #
# NCG loader                                                                   #
# --------------------------------------------------------------------------- #

def load_ncg(patient, drug, prefix=''):
    """
    Load NCG (mean ± std) from a Cell_Fates JSON file.
    prefix=''      → memory ON  (Cell_Fates_lifer_*.json)
    prefix='nomem' → memory OFF (Cell_Fates_nomem_lifer_*.json)
    """
    tag  = ('nomem_' if prefix == 'nomem' else '') + 'lifer'
    fname = os.path.join(WDIR, 'Cell_Fates_%s_%s_%s.json' % (tag, patient, drug))
    if not os.path.exists(fname):
        return None, None

    with open(fname) as f:
        data = json.load(f)

    fates = data.get('Cell_Fates_Lookup', {})
    growth = np.array(fates.get('cell_growth', []), dtype=float)
    death  = np.array(fates.get('cell_death',  []), dtype=float)

    if growth.size == 0 or death.size == 0:
        return None, None

    ncg_per_run = (growth - death) / TIME_STEPS * 100.0
    return float(np.mean(ncg_per_run)), float(np.std(ncg_per_run))

# --------------------------------------------------------------------------- #
# Collect data                                                                 #
# --------------------------------------------------------------------------- #
records = []
for patient in PATIENTS:
    for drug in DRUGS:
        ncg_on,  err_on  = load_ncg(patient, drug, prefix='')
        ncg_off, err_off = load_ncg(patient, drug, prefix='nomem')
        records.append({
            'patient': patient,
            'drug':    drug,
            'ncg_on':  ncg_on,
            'err_on':  err_on,
            'ncg_off': ncg_off,
            'err_off': err_off,
        })

# Report what's available
print('%-12s  %-35s  %10s  %10s' % ('Patient', 'Drug', 'NCG mem-ON', 'NCG mem-OFF'))
print('-' * 72)
for r in records:
    on_str  = '%.2f' % r['ncg_on']  if r['ncg_on']  is not None else '  --  '
    off_str = '%.2f' % r['ncg_off'] if r['ncg_off'] is not None else '  --  '
    diff_str = ''
    if r['ncg_on'] is not None and r['ncg_off'] is not None:
        diff_str = '  (Δ = %+.2f)' % (r['ncg_off'] - r['ncg_on'])
    print('%-12s  %-35s  %10s  %10s%s' % (
        r['patient'], r['drug'], on_str, off_str, diff_str))

# --------------------------------------------------------------------------- #
# Plot                                                                         #
# --------------------------------------------------------------------------- #
plt.rcParams.update({
    'axes.edgecolor':   'white',
    'axes.facecolor':   'white',
    'figure.facecolor': 'white',
    'figure.autolayout': True,
    'font.family':      'sans-serif',
})

fig, axes = plt.subplots(1, len(PATIENTS), sharey=True, figsize=(6 * len(PATIENTS), 6))
if len(PATIENTS) == 1:
    axes = [axes]

colors = {'on': '#4C72B0', 'off': '#DD8452'}
x      = np.arange(len(DRUGS))
width  = 0.35

for ax, patient in zip(axes, PATIENTS):
    pat_recs = [r for r in records if r['patient'] == patient]

    ncg_on  = [r['ncg_on']  if r['ncg_on']  is not None else np.nan for r in pat_recs]
    err_on  = [r['err_on']  if r['err_on']  is not None else 0       for r in pat_recs]
    ncg_off = [r['ncg_off'] if r['ncg_off'] is not None else np.nan for r in pat_recs]
    err_off = [r['err_off'] if r['err_off'] is not None else 0       for r in pat_recs]

    ax.bar(x - width/2, ncg_on,  width, yerr=err_on,  color=colors['on'],
           alpha=0.85, label='Memory ON',  edgecolor='k', capsize=4)
    ax.bar(x + width/2, ncg_off, width, yerr=err_off, color=colors['off'],
           alpha=0.85, label='Memory OFF', edgecolor='k', capsize=4)

    ax.axhline(0, color='black', linewidth=1, alpha=0.6)
    ax.set_title(patient, fontsize=16, fontweight='bold')
    ax.set_xticks(x)
    xlabels = ['\n'.join(('+' if c in d else '-') for c in CHEMO) for d in DRUGS]
    ax.set_xticklabels(xlabels, fontsize=10)
    ax.tick_params(axis='y', labelsize=12)
    ax.legend(fontsize=12)

axes[0].set_ylabel('Net Cell Growth probability (%)', fontsize=14)
fig.text(0.5, -0.02,
    'Drug combination  (A=Actinomycin, D=Doxorubicin, V=Vincristine)',
    fontsize=13, ha='center')
fig.suptitle('NCG: Memory ON vs Memory OFF', fontsize=16, fontweight='bold', y=1.02)

outfig = 'Figure_memory_comparison.png'
plt.savefig(outfig, dpi=150, facecolor='white', bbox_inches='tight')
plt.close()
print('\nSaved %s' % outfig)

# --------------------------------------------------------------------------- #
# Delta plot: (memory OFF) - (memory ON) per patient                          #
# --------------------------------------------------------------------------- #
fig2, axes2 = plt.subplots(1, len(PATIENTS), sharey=True, figsize=(6 * len(PATIENTS), 5))
if len(PATIENTS) == 1:
    axes2 = [axes2]

for ax, patient in zip(axes2, PATIENTS):
    pat_recs = [r for r in records if r['patient'] == patient]
    deltas   = []
    xlabs    = []
    for r in pat_recs:
        if r['ncg_on'] is not None and r['ncg_off'] is not None:
            deltas.append(r['ncg_off'] - r['ncg_on'])
            xlabs.append('\n'.join(('+' if c in r['drug'] else '-') for c in CHEMO))

    xi = np.arange(len(deltas))
    bar_colors = ['#e74c3c' if d < 0 else '#2ecc71' for d in deltas]
    ax.bar(xi, deltas, color=bar_colors, edgecolor='k', alpha=0.85)
    ax.axhline(0, color='black', linewidth=1)
    ax.set_xticks(xi)
    ax.set_xticklabels(xlabs, fontsize=10)
    ax.set_title(patient, fontsize=16, fontweight='bold')
    ax.tick_params(axis='y', labelsize=12)

axes2[0].set_ylabel(u'ΔNCG  (OFF − ON, %)', fontsize=14)
fig2.text(0.5, -0.02,
    'Drug combination  (A=Actinomycin, D=Doxorubicin, V=Vincristine)',
    fontsize=13, ha='center')
fig2.suptitle(u'Memory effect on NCG  (OFF − ON)', fontsize=16, fontweight='bold', y=1.02)

outfig2 = 'Figure_memory_delta.png'
plt.savefig(outfig2, dpi=150, facecolor='white', bbox_inches='tight')
plt.close()
print('Saved %s' % outfig2)
