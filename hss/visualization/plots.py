#!/usr/bin/env python

import matplotlib
matplotlib.use('Agg')
#matplotlib.use('pgf')
import numpy as np
import matplotlib.pyplot as plt
import brewer2mpl as bmpl
import string
import itertools
import pickle, json

fig_width_pt = 345.0
pt_per_inch = 72.27
golden_mean = (np.sqrt(5) - 1.0)/2
fig_width = fig_width_pt/pt_per_inch
fig_height = fig_width * golden_mean
#fig_size = [fig_width, fig_height]
fig_size = [4.0, 6.0]

"""
plt.rcParams.update({
    "pgf.texsystem": "pdflatex",
    "text.usetex" : True,
    "pgf.rcfonts" : False,
    "font.family" : "serif",
    "font.serif" : [],
    "figure.figsize" : fig_size,
    "pgf.preamble": [
         r"\usepackage[utf8x]{inputenc}",
         r"\usepackage[T1]{fontenc}",
         ]
})
"""


def plot_box(ax, position, data):
    """
    Creates the box plots of cell fate
    """
    Scatter = ax.scatter(position, data, marker = 'o', color = 'r', zorder = 10, linewidths=1.0)
    patches = ax.boxplot(data, vert=1, bootstrap=None, usermedians=None, patch_artist=True, showfliers=True, zorder = 1, medianprops = dict(color = "black"))
    boxcolors = bmpl.get_map('Set3','qualitative',len(patches["boxes"])).mpl_colors
    for patch, color in zip(patches["boxes"],boxcolors):
        patch.set(facecolor = color)
        patch.set(linewidth = 0)

def cell_fate_plot(Patient, Patient_Cell_Fates, plot_names = ["cell_death","cell_growth","net_cell_growth"], save_figure = True, lookup = False):
    """
    Gets the cell fate values as a subplot
    """
    drug_symbols = ["D",r"V\!A"]
    comb_list = list(itertools.product(['-','+'], repeat = 2))
    drug_comb_list = [] #List containing all drug combinations
    for elem in comb_list:
        drug_comb_list.append("".join(sym + "^" + stat for sym, stat in zip(drug_symbols, elem)))
    f, ax = plt.subplots(len(plot_names),sharey=True)
    Cases = [ elem.split("_", 1)[-1] for elem in Patient_Cell_Fates.keys() ]

    for num, fate in enumerate(plot_names):
        data = [] ; position = []
        for ii, case in enumerate(Cases):
            fates = Patient_Cell_Fates[Patient + "_" + case][fate]
            data.append(fates)
            position.append([ii + 1]*len(fates))
        plot_box(ax[num], position, data)
        #ax[num].set_yticks([i*0.1 for i in range(0,12,2)])
        ax[num].set_ylabel(string.capwords(fate.replace("_"," ")), fontsize = 14)

    #ax[num].set_xticklabels([r"${\mathrm %s}$" % elem for elem in drug_comb_list], fontsize = 12)
    ax[num].set_xticklabels([str(elem) for elem in drug_comb_list], fontsize = 12)
    #ax[num].set_xlabel(r"D - Doxorubcin, VA - Vincristine and Actinomycin", fontsize = 12)

    f.tight_layout()
    ax[0].set_title("Patient: %s" % Patient, fontsize = 14)
    Suffix = Patient if not lookup else Patient + "_" + "Lookup"
    if save_figure:
        print "saving cell_fates pdf"
        #f.savefig("Cell_Fates_%s.pgf" % Suffix)
        f.savefig("Cell_Fates_%s.pdf" % Suffix)

    return f

def time_course_plot(Patient, drug, integral_avg, plot_species = ["ERK_PP-cytoplasm", "AKT_P_P-cytoplasm"], save_figure = True):

    f, ax = plt.subplots(len(plot_species))
    for num, elem in enumerate(plot_species):
        #plotelem = np.transpose(np.array(integral_avg[elem].values()))
        #plotelem = np.nan_to_num(plotelem)
        #time = np.transpose(np.array(integral_avg["Time"].values()))
        minlength = min([len(timelem) for timelem in integral_avg["Time"].values()])
        for time, plotelem in zip(integral_avg["Time"].values(), integral_avg[elem].values()):
            ax[num].plot([ti/3600 for ti in time[:minlength]], plotelem[:minlength])
        ax[num].set_ylabel("%s (\#)" % elem)
        #ax[num].set_ylim([0.5*np.min(plotelem[plotmask]), 1.5*np.max(plotelem[plotmask])])
        ax[num].legend(integral_avg[elem].keys())

    ax[num].set_xlabel("Time(hrs)")
    ax[0].title.set_text("%s %s" % (Patient, drug))


    f.tight_layout()
    if save_figure:
        f.savefig("Time_Course_%s_%s.png" % (Patient, drug))

    return f
    
def Tumor_Volumes(lookup = True, drug = "Vincristine"):
    """
    Calculate and plot the tumor volumes vs cell fate
    """
    with open("Tumor_Volumes.json") as fp: Tumor_Volumes = json.load(fp)
    Delta_Volumes = { key : value["pre"] - value["post"] for key, value in Tumor_Volumes.items() }
    Delta_NCG = { "mean" : {}, "sd" : {} }
    lkey = "Average_Cell_Fate" if not lookup else "Average_Cell_Fate_Lookup"
    for key in Delta_NCG:
        with open("%s_Cell_Fata_Data.pickle" % key) as fp: avg_cell_fate = pickle.load(fp)[lkey]
        Delta_NCG["mean"][key] = avg_cell_fate[key + "_" + "Control"]["mean"]["net_cell_growth"] - avg_cell_fate[key + "_" + drug]["mean"]["net_cell_growth"]
        Delta_NCG["sd"][key] = 0.5*(avg_cell_fate[key + "_" + "Control"]["sd"]["net_cell_growth"] + avg_cell_fate[key + "_" + drug]["sd"]["net_cell_growth"])

    with open("Tumor_Volume_vs_NCG.json", "w") as fp: json.dump({"Delta_Volumes" : Delta_Volumes, "Delta_NCG" : Delta_NCG}, fp)
    plt.errorbar(Delta_Volumes.values(), Delta_NCG["mean"].values(), yerr = Delta_NCG["sd"].values())
    plt.savefig("Tumor_Volumes_%s_%s.pdf" % (lkey,drug))
