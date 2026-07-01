"""
Generate cell fate figures for the nephroblastoma hybrid model.
Run from the project root directory after loading anaconda3:
    module load anaconda3
    python3 generate_figures.py
"""

import os, json, warnings
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.ticker as mticker
from scipy import stats

warnings.filterwarnings('ignore')

wdir = 'hss/interface'

drugs = [
    'Control', 'Dox', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine',
    'Actinomycin', 'Actinomycin_Dox', 'Dox_Vincristine', 'Vincristine']
radlevels = [0]   # no radiation data available
patients = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH',
            'LAJDYMZBY4K262EJRR3V', 'KOLQXCKDRWLYVCATQAMF',
            'M2Z4XCTXSR3NCW454E5E', 'XEON5Z']
fate_names = ['cell_senescence', 'cell_death', 'cell_growth']
time_steps = 20.0
chemo = ['Actinomycin', 'Dox', 'Vincristine']

columns = ['patient', 'rad', 'drugs', 'Actinomycin', 'Dox', 'Vincristine',
           'cell_senescence', 'cell_death', 'cell_growth',
           'cell_senescence_error', 'cell_death_error', 'cell_growth_error']

# ── Load all Cell_Fates JSON files ────────────────────────────────────────────
rows = []
missing = []
for p in patients:
    for d in drugs:
        for r in radlevels:
            rm = '' if r == 0 else '_Rad_%sGy' % str(r)
            fate_filename = 'Cell_Fates_lifer_%s_%s%s.json' % (p, d, rm)
            fate_path = os.path.join(wdir, fate_filename)
            if not os.path.isfile(fate_path):
                missing.append(fate_filename)
                continue

            with open(fate_path) as fp:
                fate_data = json.load(fp)
            fates = fate_data['Cell_Fates_Lookup']

            row = {'patient': p, 'rad': r, 'drugs': d}
            for x in chemo:
                row[x] = x in d
            for f in fates:
                fate_per_step = np.array(fates[f]) / time_steps * 100
                row[f] = np.mean(fate_per_step)
                row[f + '_error'] = np.std(fate_per_step)
            rows.append(row)

if missing:
    print("Missing Cell_Fates files (skipped):", missing)

df = pd.DataFrame(rows, columns=columns)
df['net_cell_growth'] = df['cell_growth'] - df['cell_death']
df['net_cell_growth_error'] = 0.5 * (df['cell_growth_error'] + df['cell_death_error'])
print("Loaded %d conditions." % len(df))

# ── Shared style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    'axes.edgecolor': 'white', 'axes.facecolor': 'white',
    'figure.edgecolor': 'white', 'figure.facecolor': 'white',
    'figure.autolayout': True,
    'font.family': 'sans-serif',
})
palette_name = 'Paired'


# =============================================================================
# Figure 1 — Cell fate distributions (4 patients × 4 drug combos)
# =============================================================================
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ']
drugs_to_plot = ['Control', 'Dox', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine']

plotdf = df[df['drugs'].isin(drugs_to_plot) & df['patient'].isin(patients_to_plot) & (df['rad'] == 0)].copy()
plotdf['cell_fate_sum'] = plotdf['cell_growth'] + plotdf['cell_death'] + plotdf['cell_senescence']
plotdf['cell_fate_sum_mid'] = plotdf['cell_growth'] + plotdf['cell_death']

plt.style.use('fivethirtyeight')
plt.rcParams.update({'axes.edgecolor': 'white', 'axes.facecolor': 'white',
                     'figure.edgecolor': 'white', 'figure.facecolor': 'white',
                     'figure.autolayout': True, 'font.family': 'sans-serif'})

fig, ax = plt.subplots(1, 4, sharey='all', figsize=(13, 6))
for i, p in enumerate(patients_to_plot):
    patientdf = plotdf.loc[plotdf['patient'] == p]
    ax[i].set_title(('Patient = ' if i == 0 else '') + p, fontsize=18)

    sns.barplot(data=patientdf, label='Senescence',
        x='drugs', y='cell_fate_sum', edgecolor='k',
        color=sns.color_palette(palette_name)[6],
        order=drugs_to_plot, ax=ax[i])
    sns.barplot(data=patientdf, label='Growth',
        x='drugs', y='cell_fate_sum_mid', edgecolor='k',
        color=sns.color_palette(palette_name)[7],
        order=drugs_to_plot, ax=ax[i])
    death = sns.barplot(data=patientdf, label='Death',
        x='drugs', y='cell_death', edgecolor='k',
        color=sns.color_palette(palette_name)[9],
        order=drugs_to_plot, ax=ax[i])

    ax[i].set_ylabel('')
    ax[i].set_xlabel('')
    death.tick_params(axis='both', which='major', labelsize=18)

    xlabels = []
    for j, dp in enumerate(drugs_to_plot):
        xlabel = '\n'.join([(c[0] + ' ' if i + j == 0 else '') +
                            ('+' if c in dp else '-') for c in chemo])
        xlabels.append(xlabel)
    death.set_xticklabels(xlabels)

ax[0].set_ylabel('Cell fate probability (%)', fontsize=20)
for _ax in ax:
    leg = _ax.get_legend()
    if leg:
        leg.remove()
import matplotlib.patches as mpatches
leg_handles = [
    mpatches.Patch(color=sns.color_palette(palette_name)[6], label='Senescence'),
    mpatches.Patch(color=sns.color_palette(palette_name)[7], label='Growth'),
    mpatches.Patch(color=sns.color_palette(palette_name)[9], label='Death'),
]
l = fig.legend(handles=leg_handles, fontsize=16, fancybox=True,
               loc='upper left', bbox_to_anchor=(1.0, 0.98))
l.set_title('Cell Fate', prop={'size': 18})
fig.supxlabel("Simulated cytotoxic drug combinations\nA=Actinomycin, D=Doxorubicin, V=Vincristine", fontsize=20)
plt.tight_layout()
plt.savefig('Figure_1.png', dpi=600, facecolor='white', bbox_inches='tight')
plt.close()
print("Saved Figure_1.png")


# =============================================================================
# Figure 2 — Net cell growth probability per drug combo (strip plot)
# =============================================================================
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ']
drugs_to_plot = ['Control', 'Actinomycin', 'Dox', 'Actinomycin_Dox',
                 'Vincristine', 'Dox_Vincristine', 'Actinomycin_Vincristine',
                 'Actinomycin_Dox_Vincristine']

plotdf = df[df['drugs'].isin(drugs_to_plot) & df['patient'].isin(patients_to_plot) & (df['rad'] == 0)].copy()

sns.set_palette(sns.color_palette('bright'))
plt.figure(figsize=(6, 6))

graph = sns.stripplot(data=plotdf[plotdf['patient'] != 'Control'],
    x='drugs', y='net_cell_growth', edgecolor='k',
    hue='patient', order=drugs_to_plot, size=15, alpha=0.6)
graph_control = sns.stripplot(data=plotdf[plotdf['patient'] == 'Control'],
    x='drugs', y='net_cell_growth', color='black', marker='^',
    hue='patient', order=drugs_to_plot, size=15, alpha=1)

hl = [(h, l) for h, l in zip(*graph.get_legend_handles_labels())
      if l in patients_to_plot[1:]]
hl_control = [(graph_control.get_legend_handles_labels()[0][-2], 'Control')]
handles = [h for h, l in hl_control + hl]
labels  = [l for h, l in hl_control + hl]
l = plt.legend(handles, labels, fontsize=16, fancybox=True)
l.set_title('Patient', prop={'size': 18})

graph.tick_params(axis='both', which='major', labelsize=18)
graph.axhline(y=0, color='black', linewidth=1.3, alpha=0.7)

xlabels = []
for i, dp in enumerate(drugs_to_plot):
    label = '\n'.join([(c[0] + ' ' if i == 0 else '') +
                       ('+' if c in dp else '-') for c in chemo])
    xlabels.append(label)
graph.set_xticklabels(xlabels)

graph.set_ylim((-45, 110))
yticks = np.arange(-40, 110, 20)
graph.set_yticks(yticks)
graph.set_yticklabels(['{:.0f}'.format(x).ljust(4) for x in yticks])
graph.set_xlabel('Simulated cytotoxic drug\ncombinations', fontsize=20)
graph.set_ylabel('Predicted net cell growth\nprobability (%)', fontsize=20)

plt.tight_layout()
plt.savefig('Figure_2.png', dpi=800, facecolor='white')
plt.close()
print("Saved Figure_2.png")


# =============================================================================
# Figure 3 — Predicted vs. actual tumor volume change
# =============================================================================
# New patients: Actinomycin_Dox_Vincristine per Patient Data Summary note
# ("assume dox if no drug data"; explicit per-patient dose not recorded in available files).
# KOLQXCKDRWLYVCATQAMF volumes: right kidney only (bilateral tumor).
# LAJDYMZBY4K262EJRR3V volumes: raw voxels, anomalously large; ratio (post/pre) is reliable.
# XEON5Z in Pat_Mirna.json = XEON5ZV5NZIIKEAQHY4M in Tumor_Volumes.xlsx.
actual_regimens = {
    'patient': ['4L3YB6', '5XIHQG', '6Z34IQ',
                'LAJDYMZBY4K262EJRR3V', 'KOLQXCKDRWLYVCATQAMF',
                'M2Z4XCTXSR3NCW454E5E', 'XEON5Z'],
    'drugs':   ['Actinomycin_Dox_Vincristine', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine',
                'Actinomycin_Dox_Vincristine', 'Actinomycin_Dox_Vincristine',
                'Actinomycin_Dox_Vincristine', 'Actinomycin_Dox_Vincristine'],
    'rad':     [0, 0, 0, 0, 0, 0, 0],
    'pre_tumor_volume':  [287.2, 78.55, 754.75,
                          577960375.5, 15642.5, 591332.8, 107327.67],
    'post_tumor_volume': [37.48,  7.32, 147.68,
                          449203356.25, 2921.67, 857304.6, 65764.25],
}
actual_df = pd.DataFrame(data=actual_regimens)

control_df   = df[df['drugs'] == 'Control']
treatment_df = df[df['drugs'] != 'Control']
m = pd.merge(treatment_df, control_df, on=['patient', 'rad'], suffixes=('', '_control'))
m['ncg_change'] = m['cell_growth'] - m['cell_death']

ma = pd.merge(actual_df, m, on=['patient', 'drugs', 'rad'])
ma['tumor_change'] = (ma['post_tumor_volume'] / ma['pre_tumor_volume'] - 1) * 100.0
ma['ncg_change_error'] = np.sqrt(ma['cell_growth_error']**2 + ma['cell_death_error']**2)

# Short labels for long patient IDs
SHORT = {
    '4L3YB6':                 '4L3YB6',
    '5XIHQG':                 '5XIHQG',
    '6Z34IQ':                 '6Z34IQ',
    'LAJDYMZBY4K262EJRR3V':   'LAJDYM',
    'KOLQXCKDRWLYVCATQAMF':   'KOLQXC',
    'M2Z4XCTXSR3NCW454E5E':   'M2Z4XC',
    'XEON5Z':                 'XEON5Z',
}
ma['label'] = ma['patient'].map(SHORT)

ncg_control_mean = (ma['cell_growth_control'] - ma['cell_death_control']).mean()

fig, ax = plt.subplots(figsize=(11, 6))
plt.rcParams.update({'axes.edgecolor': 'white', 'axes.facecolor': 'white',
                     'figure.edgecolor': 'white', 'figure.facecolor': 'white',
                     'font.family': 'sans-serif'})

sns.set_palette(sns.color_palette('bright'))
graph = sns.scatterplot(data=ma, x='tumor_change', y='ncg_change',
    hue='label', s=80, alpha=0.85, zorder=5, ax=ax)

# Error bars from std across seeds
hdict = {lbl: h for h, lbl in zip(*graph.get_legend_handles_labels())}
for _, row in ma.iterrows():
    lbl = SHORT.get(row['patient'], row['patient'])
    h = hdict.get(lbl)
    c = h.get_facecolor()[0] if h and hasattr(h, 'get_facecolor') else (
        h.get_color() if h and hasattr(h, 'get_color') else 'gray')
    ax.errorbar(row['tumor_change'], row['ncg_change'],
                yerr=row['ncg_change_error'],
                fmt='none', color=c, capsize=4, linewidth=1.4, alpha=0.7, zorder=4)

xpad = 5
ypad = 8
xhalf = max(abs(ma['tumor_change'].min()), abs(ma['tumor_change'].max())) + xpad
yhalf = max(abs(ma['ncg_change'].min()), abs(ncg_control_mean) + 12) + ypad
xmin, xmax = -xhalf, xhalf
ymin, ymax = -yhalf, yhalf
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

ax.axhline(y=0, color='black', linewidth=1.3, alpha=0.6)
ax.axvline(x=0, color='black', linewidth=1.3, alpha=0.6)
ax.axhline(y=ncg_control_mean, color='dimgray', linewidth=1.8,
           linestyle='--', alpha=0.9, zorder=4)
ax.text(xmax - 1, ncg_control_mean + 1.5, 'Control (no drug)',
        color='dimgray', fontsize=12, ha='right', va='bottom', style='italic')

x_fit = np.linspace(xmin, xmax, 100)
mf, bf = np.polyfit(ma['tumor_change'], ma['ncg_change'], 1)
ax.plot(x_fit, mf * x_fit + bf, color='black', alpha=0.6, linewidth=1.3)

# Legend outside plot to the right
handles, labels_leg = graph.get_legend_handles_labels()
ax.get_legend().remove()
leg = ax.legend(handles, labels_leg, fontsize=12, fancybox=True,
                loc='upper left', bbox_to_anchor=(1.02, 1.0), borderaxespad=0,
                title='Patient', title_fontsize=13)

ax.tick_params(axis='both', which='major', labelsize=14)
ax.set_xlabel('Actual net tumor growth  (post/pre - 1, %)', fontsize=15, labelpad=10)
ax.set_ylabel('Predicted net cell growth  (treatment, %)', fontsize=15, labelpad=10)

plt.tight_layout()
plt.savefig('Figure_3.png', dpi=800, facecolor='white')
plt.close()
print("Saved Figure_3.png")


# =============================================================================
# Figure 2.5 — Synergy: hybrid model vs. Bliss independence vs. additive sum
# =============================================================================
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH']
singles = ['Actinomycin', 'Dox', 'Vincristine']
combos  = ['Actinomycin_Dox', 'Dox_Vincristine', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine']
drugs_to_plot_25 = singles + combos

plot_df = df[
    df['drugs'].isin(drugs_to_plot_25) &
    df['patient'].isin(patients_to_plot) &
    (df['rad'] == 0)
].copy()

issingles = plot_df['drugs'].isin(singles)

# Replace boolean columns with per-patient per-drug death probabilities
for p in patients_to_plot:
    ispatient = plot_df['patient'] == p
    plot_df.loc[ispatient, singles] = plot_df.loc[ispatient, singles].astype(float)
    for drug in singles:
        drug_mask = ispatient & (plot_df['drugs'] == drug)
        prob_vals = plot_df.loc[drug_mask, 'cell_death'].values
        prob = (prob_vals[0] / 100.0) if len(prob_vals) > 0 else 0.0
        plot_df.loc[ispatient, drug] = plot_df.loc[ispatient, drug].astype(float) * prob

plot_df['sum_rate'] = plot_df[singles].sum(axis=1) * 100.0
plot_df['sum_rate'] = plot_df['sum_rate'].clip(upper=100.0)
plot_df['indep_rate'] = (
    plot_df[singles].sum(axis=1)
    - (plot_df[['Actinomycin', 'Dox']].product(axis=1)
       + plot_df[['Actinomycin', 'Vincristine']].product(axis=1)
       + plot_df[['Dox', 'Vincristine']].product(axis=1)
       + plot_df[singles].product(axis=1))
) * 100.0

plt.rcParams.update({'font.family': 'sans-serif'})
fig, ax = plt.subplots(1, 4, sharey=True, figsize=(13, 5))

for i, p in enumerate(patients_to_plot[:4]):
    rdf = plot_df[plot_df['drugs'].isin(combos) & (plot_df['patient'] == p)]
    axi = ax[i]

    graph = sns.stripplot(data=rdf, x='drugs', y='cell_death', order=combos,
        edgecolor='k', palette=sns.color_palette('pastel'), s=15, alpha=0.8, ax=axi)
    graph_ind = sns.stripplot(data=rdf, x='drugs', y='indep_rate', order=combos,
        edgecolor='k', palette=sns.color_palette('dark'), s=15, marker='^', alpha=0.6, ax=axi)
    graph_sum = sns.stripplot(data=rdf, x='drugs', y='sum_rate', order=combos,
        edgecolor='k', palette=sns.color_palette('dark'), s=15, marker='v', alpha=0.6, ax=axi)

    axi.set_xlabel('')
    axi.set_ylabel('')

    xlabels = ['\n'.join(('+' if c in dp else '-') for c in chemo) for dp in combos]
    axi.set_xticklabels(xlabels)
    graph.tick_params(axis='both', which='major', labelsize=18)
    axi.set_title(('Patient = ' if i == 0 else '') + p)

import matplotlib.lines as mlines
leg_handles = [
    mlines.Line2D([], [], color='gray', marker='o', linestyle='None', markersize=10, label='Hybrid'),
    mlines.Line2D([], [], color='gray', marker='^', linestyle='None', markersize=10, label='Bliss'),
    mlines.Line2D([], [], color='gray', marker='v', linestyle='None', markersize=10, label='Sum'),
]
l = axi.legend(handles=leg_handles, fontsize=16, fancybox=True,
    bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
l.set_title('Model', prop={'size': 18})

ax[0].set_ylabel('Predicted cell death\nprobability (%)', fontsize=20)
fig.supxlabel('Simulated cytotoxic drug combinations\n(A=Actinomycin, D=Doxorubicin, V=Vincristine)', fontsize=20)
plt.tight_layout()
plt.savefig('Figure_2.5.png', dpi=800, facecolor='white')
plt.close()
print("Saved Figure_2.5.png")

print("\nAll figures generated.")
print("Skipped: Figure 4 (radiation — no 15/25 Gy simulation data available).")
