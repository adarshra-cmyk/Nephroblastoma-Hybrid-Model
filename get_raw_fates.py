import os
import json
from decimal import Decimal
import pandas as pd
import seaborn as sns
import numpy as np
import numpy
import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.ticker as mticker
from scipy import stats
import warnings

warnings.filterwarnings('ignore')

wdir = 'hss/interface'

drugs = [
    'Control',  'Dox', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine',
    'Actinomycin', 'Actinomycin_Dox',  'Dox_Vincristine', 'Vincristine']
radlevels = [0, 15, 25]
patients = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH']
fate_names = ['cell_senescence', 'cell_death', 'cell_growth']
time_steps = 20.0

chemo = ['Actinomycin', 'Dox', 'Vincristine']
columns=['patient','rad','drugs','Actinomycin', 'Dox', 'Vincristine',
         'cell_senescence','cell_death', 'cell_growth',
         'cell_senescence_error','cell_death_error', 'cell_growth_error']

fate_dict = {c:[] for c in columns}
rows = []
for p in patients:
    for d in drugs:
        for r in radlevels:
            row = {}
            row['patient'] = p
            for x in chemo:
                row[x] = x in d
            row['drugs'] = d
            row['rad'] = r

            # Load fates from file
            rm = '' if r==0 else '_Rad_%sGy' % str(r)
            fate_filename = 'Cell_Fates_lifer_%s_%s%s.json' % (p,d,rm) # 'Cell_Fates_ab_%s_%s%s.json'
            fate_path = os.path.join(wdir, fate_filename)
            fate_data = json.load(open(fate_path, 'rb'))
            fates = fate_data['Cell_Fates_Lookup']

            # Compute estimated probability and error per fate
            for f in fates:
                fate_per_step = np.array(fates[f])/time_steps*100
                row[f] = np.mean(fate_per_step)
                row[f + '_error'] = np.std(fate_per_step)

            rows.append(row)

# Convert to DataFrame
for row in rows:
    for col in row:
        fate_dict[col].append(row[col])
df = pd.DataFrame(data=fate_dict)

# Compute some additional summary values
df['net_cell_growth'] = df['cell_growth'] - df['cell_death']
df['net_cell_growth_error'] = 0.5*(df['cell_growth_error'] + df['cell_death_error'])

df.head(3)

# %% Figure 1 Cell Fate distributions
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ']
drugs_to_plot = ['Control', 'Dox', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine']
        # 'Vincristine', 'Dox_Vincristine', 'Actinomycin_Vincristine',
        # 'Actinomycin_Dox_Vincristine']

plotdf = df[df['drugs'].isin(drugs_to_plot) & df['patient'].isin(patients_to_plot) & (df['rad'] == 0)]
plotdf['cell_fate_sum'] = plotdf['cell_growth'] + plotdf['cell_death'] + plotdf['cell_senescence']
plotdf['cell_fate_sum_mid'] = plotdf['cell_growth'] + plotdf['cell_death']

plt.style.use('fivethirtyeight')
plt.rcParams['axes.edgecolor']='white'
plt.rcParams['axes.facecolor']='white'
plt.rcParams['figure.edgecolor']='white'
plt.rcParams['figure.facecolor']='white'
plt.rcParams['figure.autolayout']= True
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Lato']
palette_name = 'Paired'

# Background plot
fig, ax = plt.subplots(1,4, sharey='all', figsize=(13,6))

for i, p in enumerate(patients_to_plot):
    patientdf = plotdf.loc[plotdf['patient']==p]

    ax[i].set_title(('Patient = ' if i==0 else '') + p, fontsize=18)
    sen = sns.barplot(data=patientdf, label='Senescence',
        x='drugs', y='cell_fate_sum', edgecolor='k',
        color=sns.color_palette(palette_name)[6],
        order=drugs_to_plot, ax=ax[i])

    # Overlay 1
    growth = sns.barplot(data=patientdf, label='Growth',
        x='drugs', y='cell_fate_sum_mid', edgecolor='k',
        color=sns.color_palette(palette_name)[7],
        order=drugs_to_plot, ax=ax[i])

    # Overlay 2
    death = sns.barplot(data=patientdf, label='Death',
        x='drugs', y='cell_death', edgecolor='k',
        color=sns.color_palette(palette_name)[9],
        order=drugs_to_plot, ax=ax[i])

    ax[i].set_ylabel('')
    ax[i].set_xlabel('')

    # Format xticklabels
    death.tick_params(axis='both', which='major', labelsize=18)
    xlabels = []
    for j, dp in enumerate(drugs_to_plot):
        xlabel = '\n'.join([(c[0]+' ' if i+j==0 else '') +
            ('+' if c in dp else '-') for c in chemo])
        xlabels.append(xlabel)
    death.xaxis.set_ticklabels(xlabels)

# Format ylabel
ax[0].set_ylabel('Cell fate probability (%)',fontsize=20)

# Format get_legend
l = ax[-1].legend(fontsize=16, fancybox=True, bbox_to_anchor=(1.05, 1), loc=2,
    borderaxespad=0.0)
l.set_title('Cell Fate', prop={'size': 18})

plt.tight_layout()
plt.savefig('Figure_1.png', dpi=600,facecolor='white')


# %%
fig, ax = plt.subplots(figsize=(13,6))
# Format xlabel
ax.set_xlabel("Simulated cytotoxic drug combinations\nA=Actinomycin, D=Doxorubcin, V=Vincristine", fontsize = 20)
plt.savefig('Figure_1_xlabel.png', dpi=600,facecolor='white')



# %% Figure 2 Predicted outcome per simulated drug combo
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ'] #, 'ECCOAH']
# drugs_to_plot = ['Control', 'Actinomycin_Vincristine', 'Dox', 'Actinomycin_Dox_Vincristine']
drugs_to_plot = ['Control', 'Actinomycin', 'Dox', 'Actinomycin_Dox',
        'Vincristine', 'Dox_Vincristine', 'Actinomycin_Vincristine',
        'Actinomycin_Dox_Vincristine']

plotdf = df.loc[df['drugs'].isin(drugs_to_plot) & df['patient'].isin(patients_to_plot) & (df['rad'] == 0)]

sns.set_palette(sns.color_palette('bright'))
plt.figure(figsize=(6,6))

graph = sns.stripplot(data=plotdf[plotdf['patient'] != 'Control'],
    x='drugs', y='net_cell_growth', edgecolor='k',
    hue='patient', order=drugs_to_plot,
    size=15, alpha=0.6) # jitter=True,
graph_control = sns.stripplot(data=plotdf[plotdf['patient'] =='Control'],
    x='drugs', y='net_cell_growth', color='black', marker='^',
    hue='patient', order=drugs_to_plot,
    size=15, alpha=1) # jitter=True,

# Format legend for strip plot
hl = [(h,l) for h,l in zip(*graph.get_legend_handles_labels())
    if l in patients_to_plot[1:]]
hl_control = [(graph_control.get_legend_handles_labels()[0][-2],'Control')]
handles = [h for h,l in hl_control+hl]
labels = [l for h,l in hl_control+hl]

l = plt.legend(handles, labels, fontsize=16, fancybox=True)
l.set_title('Patient', prop={'size': 18})

# Change graph style
graph.tick_params(axis='both', which='major', labelsize=18)

# Generate a bolded horizontal line at y = 0
graph.axhline(y = 0, color = 'black', linewidth = 1.3, alpha = .7)

# Format xticklabels
labels = []
for i, dp in enumerate(drugs_to_plot):
    label = '\n'.join([(c[0]+' ' if i==0 else '') +
        ('+' if c in dp else '-') for c in chemo])
    labels.append(label)
graph.xaxis.set_ticklabels(labels)

# Format yticklabels
graph.set_ylim((-45, 110))
yticks = np.arange(-40,110,20)
graph.set_yticks(yticks)
yticklabels = ['{:.0f}'.format(x).ljust(4) for x in yticks]
graph.set_yticklabels(yticklabels)

# Adding a title and a subtitle
# graph.text(x = -1, y = 120, fontsize = 26, weight = 'bold', alpha = .85, s = "a")
graph.set_xlabel('Simulated cytotoxic drug\ncombinations', fontsize=20)
graph.set_ylabel('Predicted net cell growth\nprobability (%)', fontsize=20);

plt.tight_layout()
plt.savefig('Figure_2.png', dpi=800,facecolor='white')



# %% Figure 1(B)-extended Predicted outcome per patient

plt.figure(figsize=(8,6))
sns.set_palette(sns.color_palette('bright'))

graph = sns.stripplot(data=plotdf[plotdf['drugs'] != 'Control'],
    x='patient', y='net_cell_growth', hue='drugs',
    s=15, jitter=False, alpha=.6)
graph_control = sns.stripplot(data=plotdf[plotdf['drugs'] == 'Control'],
    x='patient', y='net_cell_growth',
    s=15, jitter=False, alpha=1, color='black', marker='^')

# Format legend for strip plot
hl = [(h,l) for h,l in zip(*graph.get_legend_handles_labels())
    if l in drugs_to_plot]
hl_control = [(graph_control.get_legend_handles_labels()[0][-1],'Control')]
handles = [h for h,l in hl_control+hl]
labels = [l for h,l in hl_control+hl]

for i, dp in enumerate(labels):
    label = r'$' + ''.join([(c[0]+'^' if i==0 else '') +
        ('+' if c in dp else '-') for c in chemo]) + '$'
    labels[i] = label

l = plt.legend(handles, labels, fontsize=16, fancybox=True,
    bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
l.set_title('Simulated drug\n  combinations', prop={'size': 18})

# Change graph style
graph.tick_params(axis='both', which='major', labelsize=18)

# Generate a bolded horizontal line at y = 0
graph.axhline(y = 0, color = 'black', linewidth = 1.3, alpha = .7)

# Format yticklabels
graph.set_ylim((-45, 110))
yticks = np.arange(-40,110,20)
graph.set_yticks(yticks)
yticklabels = ['{:.0f}'.format(x).ljust(4) for x in yticks]
graph.set_yticklabels(yticklabels)

# Adding a title and a subtitle
graph.text(x = -0.8, y = 120, fontsize = 26, weight = 'bold', alpha = .85, s = "b")
graph.set_xlabel('Patient', fontsize=20)
graph.set_ylabel('Predicted net cell growth probability (%)', fontsize=20);



# %%  Figure 3

# Actual treatment outcomes
actual_regimens = {'patient': ['4L3YB6', '5XIHQG', '6Z34IQ'], #, 'ECCOAH'],
                   'drugs': ['Actinomycin_Dox_Vincristine',
                        'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine'], #, 'Actinomycin_Dox_Vincristine'],  #NOT sure for last one
                   'rad': [0, 0, 0], #, 0],
                   'pre_tumor_volume': [287.2, 78.55, 754.75], #, 847.4],
                   'post_tumor_volume': [37.48, 7.32, 147.68] #, 502.65]
                   }
actual_df = pd.DataFrame(data=actual_regimens)

# Predicted treatment outcomes
control_df = df[df['drugs'] == 'Control']
treatment_df = df[df['drugs'] != 'Control']
m = pd.merge(treatment_df, control_df, on=['patient','rad'], suffixes=('', '_control'))
m['growth_change'] = m['cell_growth_control']-m['cell_growth'] #np.log(1-m['net_cell_growth'])/np.log(1-m['net_cell_growth_control'])
m['death_change'] = m['cell_death_control']-m['cell_death'] #np.log(1-m['net_cell_growth'])/np.log(1-m['net_cell_growth_control'])
m['ncg_change'] = (m['cell_growth']-m['cell_death'])#-(m['cell_growth']-m['cell_death'])

# Match across patients
ma = pd.merge(actual_df, m, on=['patient', 'drugs', 'rad'])
ma['tumor_change'] = ma['post_tumor_volume']/ma['pre_tumor_volume']*100.0

# Plot figure
plt.clf()
colors = sns.color_palette('bright')
sns.set_palette(colors)

# graph = sns.scatterplot(data=ma, x='tumor_change', y='net_cell_growth', hue='patient',
#      s=100, alpha=0.6) #yerr='ncg_change_error', xlim=(0,650), ylim=(0,1.2))
# graph = sns.scatterplot(data=ma, x='tumor_change', y='net_cell_growth_control', marker='^', hue='patient',
#      s=100, alpha=0.6) #yerr='ncg_change_error', xlim=(0,650), ylim=(0,1.2))
graph = sns.scatterplot(data=ma, x='tumor_change', y='cell_growth', marker='^', hue='patient',
     s=100, alpha=0.6) #yerr='ncg_change_error', xlim=(0,650), ylim=(0,1.2))
# graph = sns.scatterplot(data=ma, x='tumor_change', y='death_change', marker='^', hue='patient',
#      s=100, alpha=0.6) #yerr='ncg_change_error', xlim=(0,650), ylim=(0,1.2))


# %%
plt.figure(figsize=(7.5,6))
plt.rcParams['axes.edgecolor']='white'
plt.rcParams['axes.facecolor']='white'
plt.rcParams['figure.edgecolor']='white'
plt.rcParams['figure.facecolor']='white'
plt.rcParams['figure.autolayout']= True

graph = sns.scatterplot(data=ma, x='tumor_change', y='ncg_change', hue='patient',
     s=100, alpha=0.6) #yerr='ncg_change_error', xlim=(0,650), ylim=(0,1.2))

# Format legend for strip plot
handles, labels = graph.get_legend_handles_labels()
l = plt.legend(handles[1:], labels[1:], fontsize=16, fancybox=True, loc=0)
l.set_title('Patient', prop={'size': 18})

for i, p in enumerate(actual_regimens['patient']):
    x = ma[ma['patient'] == p]['tumor_change']
    y = ma[ma['patient'] == p]['ncg_change']
    graph.text(x,y-0.2,p,color=colors[i],rotation=0,weight='bold',alpha=0.8, fontsize=18)

# Change tick style
graph.tick_params(axis='both', which='major', labelsize=18)
graph.set_xlim((7.5, 22.2))
graph.set_xticks(np.arange(8,22.1,2))
graph.set_ylim((-0.1, 2.55))

# Generate a bolded horizontal line at y = 0
graph.axhline(y=0, color='black', linewidth=1.3, alpha=0.7)

# Adding a title and a subtitle
# graph.text(x=5, y=2.75, fontsize=26, weight='bold', alpha=0.85, s="c")
graph.set_xlabel('Actual tumor volume change\n(post/pre treatment %)', fontsize=20)
graph.set_ylabel('Predicted net cell growth change\n(patient/control)', fontsize=20);
graph.get_legend().remove()
# Add fit line
x = np.array([0.0,1000.0])
mf,bf = np.polyfit(ma['tumor_change'], ma['ncg_change'], 1)
plt.plot(x, mf*x+bf, color='black', alpha=0.7, linewidth=1.3)

# plt.figure(figsize=(7.5,6))
# the_table = plt.table(cellText=[['a', 'b'],['a', 'b'],['a', 'b']],
# # [['287.2\t37.48', r'Actinomycin 650 ug/kg\nVincristine 1 mg/m^2'],
# #                                 ['78.55\t7.32', r'Actinomycin 650 ug/kg\nDoxorubicin 34 mg/m^2\nVincristine 1 mg/m^2'],
# #                                 ['754.75\t148.68', r'Actinomycin 650 ug/kg\nDoxorubicin 34 mg/m^2\nVincristine 1 mg/m^2']],
#                       rowLabels=patients_to_plot[1:],
#                       colLabels=['Patient', 'Tumor volumes (ml)\n Pre\tPost treatment', 'Administered therapy'],
#                       cellLoc = 'right', rowLoc = 'center', loc='right', bbox=[1.1,.1,.3,.5])

plt.tight_layout()
plt.savefig('Figure_3.png', dpi=800, facecolor='white')




# %% Figure 1(D) Cell Fates predicted per patient with actual actual_regimens

# Plot figure
plt.clf()
colors=['#e57872', '#47b0aa']

h = ma.plot.barh(x='patient', y=['cell_death', 'cell_growth'], # _control
    rot=0, stacked=True, legend=False, xticks=np.arange(0,100.1,10),
    figsize=(6,2.5), alpha=0.8, color=colors) # color=sns.color_palette('bright'), #
h.axhline(-0.5, color='#000000',linewidth=5)

h.spines['top'].set_visible(False)
h.spines['right'].set_visible(False)
h.spines['left'].set_visible(False)
h.tick_params(bottom=False, left=False, axis='both', which='major', labelsize=18)
h.grid(axis='y')

h.set_ylabel('Patient', fontsize=20)
h.set_xlabel('Predicted cell fate probabilities\n for actual treatments (%)', fontsize=20)

h.text(0,2.5,'Cell death',color=colors[0],weight='bold', fontsize=18)
h.text(68,2.5,'Cell growth',color=colors[1],weight='bold', fontsize=18)



# %% Figure X Linear vs. quadratic model
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH']
drugs_to_plot = ['Actinomycin', 'Dox', 'Vincristine', 'Actinomycin_Dox',
    'Dox_Vincristine', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine']
singles = ['Actinomycin', 'Dox', 'Vincristine']
combos = ['Actinomycin_Dox', 'Dox_Vincristine', 'Actinomycin_Vincristine',
    'Actinomycin_Dox_Vincristine']

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Lato']

plot_df = df[df['drugs'].isin(drugs_to_plot) & df['patient'].isin(patients_to_plot) & (df['rad'] == 0)]
issingles = plot_df['drugs'].isin(singles)

for p in patients_to_plot:
    ispatient = plot_df['patient']==p
    probs = plot_df.loc[ispatient & issingles, 'cell_death'].to_numpy()
    plot_df.loc[ispatient, singles] *= probs/100.0

plot_df['sum_rate'] = plot_df[singles].sum(axis=1)*100.0
plot_df.sum_rate[plot_df['sum_rate'] > 100.0] = 100.0
plot_df['indep_rate'] = plot_df[singles].sum(axis=1) \
    - (plot_df[['Actinomycin','Dox']].product(axis=1) \
    + plot_df[['Actinomycin','Vincristine']].product(axis=1) \
    + plot_df[['Dox','Vincristine']].product(axis=1)
    + plot_df[singles].product(axis=1))
plot_df['indep_rate'] *= 100.0

fig,ax = plt.subplots(1,4, sharey=True, figsize=(13,5))

for i, p in enumerate(patients_to_plot[:4]):
    rdf = plot_df[plot_df['drugs'].isin(combos) & (plot_df['patient'] == p)]
    axi = ax[i]
    graph = sns.stripplot(data=rdf,
        x='drugs', y='cell_death', order=combos, edgecolor='k',
        palette=sns.color_palette('pastel'),
        s=15, alpha=0.8, ax=axi)
    graph_ind = sns.stripplot(data=rdf,
        x='drugs', y='indep_rate', order=combos, edgecolor='k',
        palette=sns.color_palette('dark'),
        s=15, marker='^', alpha=0.6, ax=axi)
    graph_sum = sns.stripplot(data=rdf,
        x='drugs', y='sum_rate', order=combos, edgecolor='k',
        palette=sns.color_palette('dark'),
        s=15, marker='v', alpha=0.6, ax=axi)
    axi.set_xlabel('')
    axi.set_ylabel('')

    # Format xticklabels
    labels = []
    for j, dp in enumerate(combos):
        label = '\n'.join([('+' if c in dp else '-') for c in chemo])
        labels.append(label)
    axi.xaxis.set_ticklabels(labels)

    graph.tick_params(axis='both', which='major', labelsize=18)
    graph.set_title( ('Patient = ' if i==0 else '') + p)

handles = np.array(graph.get_legend_handles_labels()[0])[[8,4,0]]
l = axi.legend(handles, ['Sum', 'Bliss', 'Hybrid'],
    fontsize=16, fancybox=True, bbox_to_anchor=(1.05, 1), loc=2,
    borderaxespad=0.0)
l.set_title('Model', prop={'size': 18})

plt.tight_layout()
plt.savefig('Figure_2.5.png', dpi=800,facecolor='white')



# %% Figure 2.5 axis labelsize
fig,ax = plt.subplots(figsize=(13,5))
ax.set_xlabel('Simulated cytotoxic drug combinations\n(A=Actinomycin, D=Doxorubicin, V=Vincristine)', fontsize=20)
ax.set_ylabel('Predicted cell death\nprobability (%)', fontsize=20);

# Format xticklabels
labels = []
for j, dp in enumerate(combos):
    label = '\nA\nD\nV'
    labels.append(label)
ax.xaxis.set_ticklabels(labels)
plt.tight_layout()
plt.savefig('Figure_2.5_labels.png', dpi=800,facecolor='white')



# %%

# plot_df['prod rate'] = (1.0 - np.exp((1.0 - plot_df[singles]).applymap(np.log).sum(axis=1))) * 100.0 # same as indepdent rate
plot_df['sum rate'] = plot_df[singles].sum(axis=1) * 100.0
plot_df['Obs-Pred'] = plot_df['cell_death'] - plot_df['indep_rate']
plot_df['sum log(death)'] = np.exp(plot_df[singles].applymap(np.log).replace(-np.inf, 0).sum(axis=1))
print plot_df[['patient', 'drugs', 'cell_death', 'indep_rate']]#, 'prod rate']] # 'sum death', 'sum log(death)',

# %%
combo_rates = plot_df.loc[plot_df['indep_rate']>0]
print stats.ttest_ind(combo_rates['cell_death'], combo_rates['indep_rate'])
print stats.ttest_ind(combo_rates.loc[(combo_rates['patient']!='Control'), ['cell_death','indep_rate']],
    combo_rates.loc[(combo_rates['patient'].isin(['4L3YB6', '5XIHQG', '6Z34IQ'])), ['cell_death','indep_rate']])
print stats.ttest_ind(plot_df.loc[(plot_df['patient']!='Control'), ['cell_death','cell_growth']],
    plot_df.loc[(plot_df['patient'].isin(['4L3YB6', '5XIHQG', '6Z34IQ'])), ['cell_death','cell_growth']])



# %%
plt.clf()
plt.figure(figsize=(6,6))

graph = sns.stripplot(data=plotdf[plotdf['patient'] != 'Control'],
    x='drugs', y='net_cell_growth', edgecolor='k',
    hue='patient', order=drugs_to_plot,
    jitter=True, size=15, alpha=0.6)
graph_control = sns.stripplot(data=plotdf[plotdf['patient'] =='Control'],
    x='drugs', y='net_cell_growth', color='black', marker='^',
    hue='patient', order=drugs_to_plot,
    jitter=True, size=15, alpha=1)

graph = sns.catplot(data=plotdf, x='drugs', y='net_cell_growth') #col)

# Format legend for strip plot
hl = [(h,l) for h,l in zip(*graph.get_legend_handles_labels())
    if l in patients_to_plot[1:]]
hl_control = [(graph_control.get_legend_handles_labels()[0][-2],'Control')]
handles = [h for h,l in hl_control+hl]
labels = [l for h,l in hl_control+hl]

l = plt.legend(handles, labels, fontsize=16, fancybox=True)
l.set_title('Patient', prop={'size': 18})

# Change graph style
graph.tick_params(axis='both', which='major', labelsize=18)

# Generate a bolded horizontal line at y = 0
graph.axhline(y = 0, color = 'black', linewidth = 1.3, alpha = .7)

# Format xticklabels
labels = []
for i, dp in enumerate(drugs_to_plot):
    label = '\n'.join([(c[0]+' ' if i==0 else '') +
        ('+' if c in dp else '-') for c in chemo])
    labels.append(label)
graph.xaxis.set_ticklabels(labels)

# Format yticklabels
graph.set_ylim((-45, 110))
yticks = np.arange(-40,110,20)
graph.set_yticks(yticks)
yticklabels = ['{:.0f}'.format(x).ljust(4) for x in yticks]
graph.set_yticklabels(yticklabels)

# Adding a title and a subtitle
graph.text(x = -1, y = 120, fontsize = 26, weight = 'bold', alpha = .85, s = "a")
graph.set_xlabel('Simulated cytotoxic drug combinations', fontsize=20)
graph.set_ylabel('Predicted net cell growth probability (%)', fontsize=20);



# %% Figure 4 Radiation
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH']
drugs_to_plot=['Control', 'Dox', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine']

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Lato']
sns.set_palette(sns.color_palette('bright'))

fig, ax = plt.subplots(2,2, sharex='all', sharey='row', figsize=(8,8))
axis_choice = [(0,0), (0,1),(1,0),(1,1)]
drug_titles = [r'$A^- D^- V^-$', r'$A^- D^+ V^-$', r'$A^+ D^- V^+$', r'$A^+ D^+ V^+$']

for i, d in enumerate(drugs_to_plot):
    plotdf = df[df['drugs']==d]

    plotdf['adjusted_cell_death'] = 100.0*(1 - (1 - plotdf['cell_death']/100.0)*np.exp(-0.00875*np.power(plotdf['rad'],2)))
    plotdf['adjusted_net_growth'] = plotdf['cell_growth']-plotdf['adjusted_cell_death']

    axi = ax[axis_choice[i]]

    graph = sns.scatterplot(data=plotdf[plotdf['patient'] != 'Control'],
        x='rad', y='adjusted_net_growth',hue='patient', s=300,
        alpha=0.6, ax=axi)
    graph_control = sns.scatterplot(data=plotdf[plotdf['patient'] =='Control'],
        x='rad', y='adjusted_net_growth', palette=['black'], marker='^', hue='patient',
        s=300, alpha=1, ax=axi)

    axi.get_legend().remove()
    axi.tick_params(axis='both', labelsize=18)
    axi.set_title(drug_titles[i])
    axi.set_xlabel('')
    axi.set_ylabel('')
    axi.set_xticks([0,15,25])

# Format legend for strip plot
hl = [(h,l) for h,l in zip(*graph.get_legend_handles_labels())
    if l in patients_to_plot[1:]]
hl_control = [(graph_control.get_legend_handles_labels()[0][-1],'Control')]
handles = [h for h,l in hl_control+hl]
labels = [l for h,l in hl_control+hl]

l = ax[(0,1)].legend(handles, labels, fontsize=16, fancybox=True,
    bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
l.set_title('Patient', prop={'size': 18})

# Save
plt.tight_layout()
plt.savefig('Figure_4.png', dpi=800,facecolor='white')

# %%
af = 0.035
bf = 0.0035
S = np.exp(-15*af)*np.exp(-15*15*bf)
print S
# %% Axis labels for figure
fig, ax = plt.subplots(figsize=(8,8))
ax.set_ylabel('Predicted net cell growth\nprobability (%)', fontsize=20)
ax.set_xlabel("Radiation therapy dosage (Gy)", fontsize = 20)
plt.savefig('Figure_4_xlabel.png', dpi=800,facecolor='white')



# %% Figure 4 Radiation - version 2

drugs = [
    'Control',  'Dox', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine']
radlevels = [0, 15, 25]
patients = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH']
fate_names = ['cell_senescence', 'cell_death', 'cell_growth']
time_steps = 20.0

chemo = ['Actinomycin', 'Dox', 'Vincristine']
columns=['patient','rad','drugs','Actinomycin', 'Dox', 'Vincristine',
         'cell_senescence','cell_death', 'cell_growth',
         'cell_senescence_error','cell_death_error', 'cell_growth_error']

fate_dict = {c:[] for c in columns}
rows = []
for p in patients:
    for d in drugs:
        for r in radlevels:
            row = {}
            row['patient'] = p
            for x in chemo:
                row[x] = x in d
            row['drugs'] = d
            row['rad'] = r

            # Load fates from file
            rm = '' if r==0 else '_Rad_%sGy' % str(r)
            fate_filename = 'Cell_Fates_%s_%s_%s%s.json' % ('lifer' if r==0 else 'ab', p,d,rm)
            fate_path = os.path.join(wdir, fate_filename)
            fate_data = json.load(open(fate_path, 'rb'))
            fates = fate_data['Cell_Fates_Lookup']

            # Compute estimated probability and error per fate
            for f in fates:
                fate_per_step = np.array(fates[f])/time_steps*100
                row[f] = np.mean(fate_per_step)
                row[f + '_error'] = np.std(fate_per_step)

            rows.append(row)

# Convert to DataFrame
for row in rows:
    for col in row:
        fate_dict[col].append(row[col])
rdf = pd.DataFrame(data=fate_dict)

# Compute some additional summary values
rdf['net_cell_growth'] = rdf['cell_growth'] - rdf['cell_death']
rdf['net_cell_growth_error'] = 0.5*(rdf['cell_growth_error'] + rdf['cell_death_error'])


# %% plot
patients_to_plot = ['Control', '4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH']
drugs_to_plot=['Control', 'Dox', 'Actinomycin_Vincristine', 'Actinomycin_Dox_Vincristine']

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Lato']
sns.set_palette(sns.color_palette('bright'))

fig, ax = plt.subplots(2,2, sharex='all', sharey='row', figsize=(8,8))
axis_choice = [(0,0), (0,1),(1,0),(1,1)]
drug_titles = [r'$A^- D^- V^-$', r'$A^- D^+ V^-$', r'$A^+ D^- V^+$', r'$A^+ D^+ V^+$']

for i, d in enumerate(drugs_to_plot):
    plotdf = rdf[rdf['drugs']==d]

    plotdf['adjusted_cell_death'] = 100.0*(1 - (1 - plotdf['cell_death']/100.0)*np.exp(-0.0051*np.power(plotdf['rad'],2)))
    plotdf['adjusted_net_growth'] = plotdf['cell_growth']-plotdf['adjusted_cell_death']

    axi = ax[axis_choice[i]]

    graph = sns.scatterplot(data=plotdf[plotdf['patient'] != 'Control'],
        x='rad', y='adjusted_net_growth',hue='patient', s=300,
        alpha=0.6, ax=axi)
    graph_control = sns.scatterplot(data=plotdf[plotdf['patient'] =='Control'],
        x='rad', y='adjusted_net_growth', palette=['black'], marker='^', hue='patient',
        s=300, alpha=1, ax=axi)

    axi.get_legend().remove()
    axi.tick_params(axis='both', labelsize=18)
    axi.set_title(drug_titles[i])
    axi.set_xlabel('')
    axi.set_ylabel('')
    axi.set_xticks([0,15,25])

# Format legend for strip plot
hl = [(h,l) for h,l in zip(*graph.get_legend_handles_labels())
    if l in patients_to_plot[1:]]
hl_control = [(graph_control.get_legend_handles_labels()[0][-1],'Control')]
handles = [h for h,l in hl_control+hl]
labels = [l for h,l in hl_control+hl]

l = ax[(0,1)].legend(handles, labels, fontsize=16, fancybox=True,
    bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
l.set_title('Patient', prop={'size': 18})

# Save
plt.tight_layout()
plt.savefig('Figure_4_v2.png', dpi=800,facecolor='white')



# %% Figure 5 Linear quadratic model comparison
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Lato']
fig, ax = plt.subplots(1,1, figsize=(8,8))

plotdf = df[(df['patient']=='Control') & (df['drugs']=='Control')]

plotdf['adjusted_cell_death'] = 100.0*(1 - (1 - plotdf['cell_death']/100.0)*np.exp(-0.0051*np.power(plotdf['rad'],2)))
plotdf['adjusted_net_growth'] = (plotdf['cell_growth']-plotdf['adjusted_cell_death'])/100.0

plotdf.head(3)

plt.plot(plotdf['rad'],(plotdf['cell_growth']-plotdf['adjusted_cell_death'])/100.0, label='Hybrid')

d = np.arange(0,25,0.1)

alpha_betas=[[3.7e-2,2.8e-3],[2.0e-2,5.1e-3], [0.5e-2, 09.2e-3]] # [13e-2, 2.5e-3]
for (a,b) in alpha_betas:
    y = np.exp(-a*d-b*np.power(d,2))
    plt.plot(d,y,label=r'LQ ($\alpha$={:.1e}, '.format(a)
        + r'$\beta$={:.1e}, '.format(b)
        + r'$\alpha/\beta={:.2f}$ Gy)'.format(a/b))

l = plt.legend(fontsize=16)
l.set_title('Model', prop={'size': 18})
ax.set_ylabel('Predicted cell survival probability (%)', fontsize=20)
ax.set_xlabel("Radiation therapy dosage (Gy)", fontsize = 20)

ax.tick_params(axis='both', labelsize=18)
plt.savefig('Figure_5.png', dpi=800,facecolor='white')

from matplotlib.font_manager import findfont, FontProperties
font = findfont(FontProperties(family=['sans-serif']))
print font


# %% Table 1 List of differential patient miRNA with targets maybe
from upsetplot import plot

model_species = ['RTK', 'MEK', 'Pase1', 'Pase2', 'Pase3', 'PDK1', 'Shp', 'PIP3',
                'Shp2', 'PI3K', 'PIP2', 'Pase9t', 'Ser', 'Raf', 'Gab1', 'GAP',
                'Grb2', 'cPP', 'ATM', 'Ras', 'Sos', 'Shc', 'GDP', 'GTP', 'ERK',
                'EGF', 'PTEN', 'AKT', 'ErbB1', 'ErbB2','ErbB3', 'ErbB4', 'HRG']
patient_mods = {
    '4L3YB6': ["E2F1","WIP1","CDKN1A","RB1","CASP9","CCNG1","CDK2","BAX","ARF","MDM2","MDM4","BCL2"],
    '5XIHQG': ["E2F1","WIP1","BAX","CASP9","CCNG1","RB1","ARF","MDM2","MDM4"],
    '6Z34IQ	':["E2F1","WIP1","RB1","CASP9","CCNG1","CDK2","BAX","ARF","MDM2","BCL2"],
    'ECCOAH': ["E2F1","WIP1","RB1","CASP9","CCNG1","CDK2","BAX","ARF","MDM2","MDM4","BCL2"]}
umods = list(np.unique([j for i in patient_mods.values() for j in i])) \
        + ['EGF', 'PTEN', 'AKT', 'TP53', 'ERK', 'Raf', 'AKT1'] + model_species \
        + ['WT1', 'CTNNB1', 'AMER1', 'IGF2', 'MYCN', 'SIX1', 'SIX2', 'SMARCA4',
        'MLLT1', 'NF1', 'BORCL1', 'COL6A3', 'NONO', 'BRD7', 'ARID1A', 'FFGR1',
        'MAX', 'MAP3K4', 'BCOR', 'ARID1A', 'ASXL1', 'HDAC4', 'CHD4', 'ACTB']
umods = np.char.upper(umods)
print umods
patients = ['4L3YB6', '5XIHQG', '6Z34IQ', 'ECCOAH']
dir = '/Users/lindsey/Research/copasi_models/nephroblastoma_hybrid_model/hss/io'

data = {}
for p in patients:
    path = os.path.join(dir, 'miRNA_Targets_%s_Control.json' % p)
    data[p] = json.load(open(path, 'rb'))

targets = {}
for p in patients:
    for m in data[p].keys():
        t = np.sort(data[p][m]['target mRNA'])
        tu = np.intersect1d(t, umods)
        targets[m] = ', '.join(tu)
mirna = targets.keys()

mdf = pd.DataFrame({'miRNA': mirna, 'targets': [targets[m] for m in mirna]})
for p in patients:
    mdf[p] = mdf['miRNA'].isin(data[p].keys())

# mdf['sum'] = mdf[patients].sum(axis=1)
mdf[patients] = mdf[patients].replace(True, u'\u2713')
mdf[patients] = mdf[patients].replace(False, '')
hdf = dmf[mdf['targets']!=''] # 33 of 75 have known targets

# hdf[patients].drop_duplicates()

hdf.sort_values(by=patients).style
