#!/usr/bin/env python

"""
This script is used to take the patient
miRNA data and drug information as input and modify the
initialization information for the individual components of the
hybrid model. For example, if certain miRNA are overexpressed
that directly influence a particular mRNA, then their initial
expression levels will be adjusted appropriately.

Example Run
-----------
This script is invoked from the command line as below

    $ ./preprocessor.py -p <patient-id> -d "Drug1,Drug2" \\
    ../interface/Run_Info.json

In the above run `<patient-id>` is the pseudo anonymized id of the
patient and `Drug1` etc are the name of the drug. Currently only
Dox and Vincristine are drugs that are supported. If the options
`-p` and/or `-d` are not provided then these are assumed as control
patient and no drug conditions respectively.

Input Files
-----------
The file [`Run_Info.json`](../hss/interface/Run_Info.json) located in the folder `hss/interface` is
the input file which is provided as the command line argument. This
file contains the location of the input files for ODE and the Boolean
models and various drug specific information.

Output Data
-----------
The main output data are the modified versions of the Boolean
model with the specific changes in node status and drug related
information. This file is named based on the name of the input
file provided in `Run_Info.json` file with the simulation id
appended to it. The other file is a modified version of the
`Run_Info.json` file itself with information related to ODE
specific changes.

Dependencies
-------------

- Python >= 2.7
- [`change`](change.m.html) module (local)

"""

import os, sys
import csv, json
import xml.etree.ElementTree as ET
import change
from optparse import OptionParser

species_pattern = r"CN=Root,Model=(?P<model>[^,]+),Vector=Compartments\[(?P<compartment>[^]]+)\],Vector=Metabolites\[(?P<species>[^]]+)\]"
'''This is a regex pattern to locate a particular species in the Copasi file. The regex captures the name of model, compartment and the species.'''

Indicator_Nodes = {
    "G1toS" : ["CDK2","CASP9"],
    "G2toM" : ["BCL2"]
    }
'''This is contains the list of specific nodes that indicate cell fate in two different stages of cell cycle G1-S transition and G2-M transition.'''

Indicators = {
    "G1toS" : [
            [{"CDK2" : 1, "CASP9" : 0}, "cell_growth"],
            [{"CDK2" : 0, "CASP9" : 1}, "cell_death"],
            [{"CDK2" : 1, "CASP9" : 1}, "cell_growth"],
            [{"CDK2" : 0, "CASP9" : 0}, "cell_senescence"]
            ],
    "G2toM" : [
            [{"BCL2" : 0}, "cell_death"],
            [{"BCL2" : 1}, "cell_growth"]
            ]
    }
'''This dictionary shows how the steady-state status of the indicator nodes of the Boolean model maps to a specific cell fate. These are crude approximations especially because not much information is available regarding G2-M transition. This may need to be modified as and when more information is available.'''

def Xml_to_Csv(mirna_file):
    """
    Writes a csv file from xml
    
    Parameters
    ----------
    - `mirna_file` : `str` Name of the mirna file in XML (minML)
    format.
    
    Returns
    -------
    `str` Name of the converted csv file
    """
    root = change.Generate_Xml(mirna_file)
    data = root.find("Sample").find("Data-Table").find("Internal-Data")
    csvfile = os.path.splitext(mirna_file)[0] + ".csv"
    with open(csvfile, "w") as fp: fp.write(data.text)

    return csvfile

def Top_Mirna(mirna_file, delim = '\t', top = 20):
    """
    This gets a list of top 20 (default) miRNA names
    which are differentially expressed relative to control.
    
    Parameters
    ----------
    - `mirna_file` : `str` Name of the files containing miRNA
    expression data in XML or csv format.
    - `delim` : `str` The delimiter to be used for parsing the
    miRNA expression data, which is tab separated by default.
    - `top` : `int` The number of top genes to include in the
    final result

    Returns
    -------
    `list` A list of tuples containing the gene names and their
    expression numbers.
    """
    if os.path.splitext(mirna_file)[-1] == ".xml":
        mirna_file = Xml_to_Csv(mirna_file)

    linc = 0
    mirna_data = {}
    with open(mirna_file) as fp:
        for org_line in fp:
            line = org_line.strip()
            if line:
                if linc == 0:
                    linc += 1
                    continue
                else:
                    mirna, expr = line.split(delim)
                    mirna_data[mirna] = float(expr)
                    linc += 1
    sorted_mirna_data = sorted(mirna_data.items(), key = lambda x: x[1], reverse = True)

    #top_mirna = [ key for key, value in sorted_mirna_data[:top] ]
    return sorted_mirna_data[:top]

def Mirna_Targets(mirna_names, mirtarfile, writefile = ""):
    """
    Obtains the target mRNA list from a list of miRNA names
    using [miRTarBase](http://mirtarbase.mbc.nctu.edu.tw/php/index.php).
    Download a recent version of the data if necessary.
    
    Parameters
    ----------
    - `mirna_names` : `list` A sorted list of miRNA names that are
    differentially expressed relative to control patient.
    - `mirtarfile` : `str` The name of the file containing 
    downloaded data from miRTarBase.
    - `writefile` : `str` An optional argument that specifies whether
    the target mRNA names will be written to a file or not. Default
    value is empty string which skips the write step.

    Returns
    -------
    `dict` : A dictionary that contains each miRNA name as key and
    the list of target miRNA it suppresses as values.
    """
    mirna_targets = {
        key : {
            "expression" : value,
            "target mRNA" : set()
        } for key, value in mirna_names }

    with open(mirtarfile) as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            if row["miRNA"] in mirna_targets.keys():
                mirna_targets[row["miRNA"]]["target mRNA"].update((row["Target Gene"],))

    for key in mirna_targets:
        mirna_targets[key]["target mRNA"] = list(mirna_targets[key]["target mRNA"]) 

    if writefile != "":
        with open(writefile, "w") as fp: json.dump(mirna_targets, fp)

    return mirna_targets
        
def Direct_Mrna_Targets(species,mirna_targets):
    """
    Finds which target genes of the top miRNAs are present in
    the individual components of the hybrid model.

    Parameters
    ----------
    - `species` : `list` A list of all gene names in the current
    network.
    - `mirna_target` : `dict` The names of miRNAs and their target
    genes.

    Returns
    -------
    `list` A list of target genes which are direct targets of the
    miRNAs.
    """
    target_set = set()
    for key,value in mirna_targets.items():
        target_set.update(set(species) & set(value["target mRNA"]))

    return list(target_set)

def Copasi_Species(Cpsfile, name_filter = r"[a-zA-Z0-9]+\Z", Speciesfile="Network_Species.json"):
    """
    Gets a list species from the Copasi XML file. It uses a
    simplistic logic to filter out species which are complexes
    by ignoring any compound words such as `ErbB1:ErbB4` as the
    name of EGFR-HER4 heterodimer. It uses the `change.Generate_Xml`
    and `change.Get_Elem` functions to find the matches.
    
    Parameters
    ----------
    - `Cpsfile` : `str` Path to the Cpsfiles from which the species
    name is to be extracted.
    - `name_filter` : A regex pattern that is used to filter out
    the names of the species.
    - `Speciesfile` : An optional argument that contains the names
    of the species in the Copasi file from previous runs. If this
    file is present then this function call may be skipped.

    Returns
    -------
    `tuple` A tuple containing two lists. One is the name of the
    species in capitalized form which is used by most databases
    including miRTarBase. The second one is actual name and the
    compartment it is found.
    """
    root = change.Generate_Xml(Cpsfile)
    XPathstr = ".//*[@cn='String=Initial Species Values']"
    Species_Elem = change.Get_Elem(root, XPathstr)
    species_list = []
    species_values = {}
    for elem in Species_Elem:
        match = change.Cps_Name(elem, species_pattern)
        if match is not None:
            species_list.append([match["species"],match["compartment"]])
            species_values[match["species"] + "-" + match["compartment"]] = elem.get("value")
    species_word = { elem[0].upper() : elem for elem in species_list if ET.re.match(name_filter, elem[0]) }

    if Speciesfile != "":
        with open(Speciesfile,"w") as fp: json.dump(species_word, fp, indent = 4)
        Speciesvaluefile = os.path.splitext(Speciesfile)[0] + "_Values" + ".json"
        with open(Speciesvaluefile, "w") as fp: json.dump(species_values, fp, indent = 4)
        print "Species Names written in file %s, check and ensure correct gene IDs" % Speciesfile

    return species_word, species_values


class Drugs:
    """
    Class to determine drug dosage and thresholds
    
    This class is used to to store information related to
    drugs such as their threshold values, nodes they influence
    and also the methods used to calculate their base values.
    
    Attributes
    ----------
    - `name` : `str` Name of the drug
    - `initialize` : `dict` A dictionary containing information
    about the drug such as its threshold and actual dosage.
    
    Methods
    -------
    - `find_nodes()`
       Gets the list of nodes that are influenced by the drug
    - `calc_base()`
       Calculates the base value of the drug from dosage and
       threshold information.

    """

    def __init__(self, name, initialize):

        self.name = name
        """Name of the drug"""
        self.initialize = initialize
        """A dictionary containing information about the drug
        such as its dosage and threshold information."""

    def find_nodes(self):
        """
        Finds the list of nodes affected by the given drug.
        
        Returns
        -------
        `list` A list of nodes which are affected by the drug.
        """
        if self.initialize["dosage"] > self.initialize["threshold"]:
            self.nodes = self.initialize["nodes"]
        else:
            self.nodes = []

        return self.nodes

    def calc_base(self):
        """
        Gets the base value of the drug using dosage and specific
        coefficient. Uses a Hill function.
        
        Returns
        -------
        `float` The base value of the drug.
        """
        Base = lambda kd, dosage, coeff : int(round(3/( ( (kd/dosage)**coeff ) + 1)))
        if self.initialize["dosage"] > self.initialize["threshold"]:
            self.base = Base(self.initialize["KD"], self.initialize["dosage"], self.initialize["coeff"])
        else:
            self.base = 0

        return self.base

    def __str__(self):

        return "Drug(name = %s, dosage = %2.2f)" % (self.name, self.initialize["dosage"])
    
if __name__ == '__main__':

    #Configfile = "../interface/Run_Info.json"
    usage = "Usage: %prog [options] Configfile"
    parser = OptionParser(usage = usage)
    parser.set_defaults(patient_id = "Control", drug = "Control", radiation = "0")
    parser.add_option("-p", "--patient-id", dest = "patient_id", help = "The id of the patient for which miRNA data is available")
    parser.add_option("-d", "--drug", dest = "drug", help = "Name of the drug to be dosed, specify multiple drugs separated by commas")
    parser.add_option("-r", "--radiation", dest = "radiation", help = "Radiation dosage, specified in Gy")
    parser.add_option("-s", "--suffix", dest = "suffix", help = "Additional identifier suffix to tack onto output files")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error(usage)
    elif not os.path.isfile(args[0]):
        parser.error("File %s not found" % args[0])
    else:
        with open(args[0]) as fp: Run_Info = json.load(fp)
    Networktempfile = "Network_Species_Temp.json"
    boolean_changes = { "states" : {}, "bases" : {} }
    Restricted_Nodes = []  #Nodes that are restricted by mirna or drug
    ode_network_targets = []
    druglist = options.drug.replace(" ","").split(",")

    Run_Info["run_id"] = options.patient_id + "_" + "_".join(druglist)

    if options.drug != "Control":
        for elem in druglist:
            Run_Info["drug"][elem]["status"] = "on"
    try:
        Run_Info["Radiation"]["dosage"] = float(options.radiation)
    except ValueError:
        parser.error("Incorrect radiation dosage format %s" % options.radiation)

    Run_Info["run_id"] += "_Rad_" + options.radiation + "Gy" if float(options.radiation) > 0 else ""

    suffix = "_%s" % Run_Info["run_id"]

    if options.suffix:
        Run_Info["run_id"] = options.suffix + "_" + Run_Info["run_id"]

    with open(Run_Info["models"]["choibool"]["file"]) as fp: boolmodel = json.load(fp)

    if options.patient_id != "Control":
        Run_Info["mirna"]["mirna_file"] = "mirna_data/miRNA_%s.xml" % options.patient_id
        mirna_target_file = "miRNA_Targets%s.json" % suffix

        #Preprocess mirna data
        try:
            with open(mirna_target_file) as fp: mirna_targets = json.load(fp)
        except IOError:
            print "%s not found, creating new file" % mirna_target_file
            top_mirna = Top_Mirna(Run_Info["mirna"]["mirna_file"], top = Run_Info["mirna"]["top"])
            mirna_targets = Mirna_Targets(top_mirna, Run_Info["mirna"]["mirtarfile"], writefile = mirna_target_file)
        except ValueError:
            res = raw_input("Json file %s not readable, create and overwrite file?(y/n): " % mirna_target_file)
            if res == "y":
                top_mirna = Top_Mirna(Run_Info["mirna"]["mirna_file"], top = Run_Info["mirna"]["top"])
                mirna_targets = Mirna_Targets(top_mirna, Run_Info["mirna"]["mirtarfile"], writefile = mirna_target_file)
            else:
                print "Program Aborted"
                quit()
        except Exception:
            raise
        else:
            print "mirna targets loaded from %s" % mirna_target_file
        
        target_mrna = Direct_Mrna_Targets(boolmodel["network"].keys(), mirna_targets)
        for key in target_mrna:
            boolean_changes["states"][key] = 0
            boolmodel["network"][key]["initial_state"] = 0
        Restricted_Nodes.extend(target_mrna)
        species_words, species_values = Copasi_Species(Run_Info["models"]["chenode"]["file"], Speciesfile = Networktempfile)
        #res = raw_input("Check file %s, type y to continue, q to quit: " % Networktempfile)
        #if res == 'q':
        #    quit()
        with open("Network_Species_Temp.json") as fp: ode_network = json.load(fp)
        species = ode_network.keys()
        ode_network_direct = Direct_Mrna_Targets(species, mirna_targets)
        ode_network_targets = [ value for key, value in ode_network.items() if key in ode_network_direct ]

    #Preprocess Drug data
    boolmodel["cell_states"] = {}
    for key, value in Run_Info["drug"].items():
        if value["status"] == "on":
            drug = Drugs(key, value)
            base, nodes = drug.calc_base(), drug.find_nodes()
            Restricted_Nodes.extend(nodes)
            for node in nodes:
                boolean_changes["states"][node] = 1
                boolmodel["network"][node]["initial_state"] = 1
            boolmodel["network"]["ATM"]["base"] = base
            boolmodel["network"]["ARF"]["base"] = 0


    boolmodel["cell_states"] = Indicators
    boolmodel["changes"].update(boolean_changes)
    boolmodel["indicator_nodes"] = Indicator_Nodes
    name, ext = os.path.splitext(Run_Info["models"]["choibool"]["file"])
    booloutfilename = name + suffix + ext

    with open(booloutfilename, "w") as fp: json.dump(boolmodel, fp, indent = 4)
    Run_Info["models"]["choibool"]["modfile"] = booloutfilename
    Run_Info["models"]["choibool"]["Restricted_Nodes"] = list(set(Restricted_Nodes))

    ode_changes = [
        {
            "Paramtype" : "Initial Species Values",
            "substitute" : {
                "compartment" : key[-1],
                "species" : key[0]
            },
            "value" : 0.6*round(float(species_values['-'.join(key)]), 3)
        } for key in ode_network_targets ]

    Run_Info["models"]["chenode"]["initialize"].extend(ode_changes)

    Configoutfile = os.path.splitext(args[0])[0] + suffix + ".json"

    with open(Configoutfile, "w") as fp: json.dump(Run_Info, fp)
    
