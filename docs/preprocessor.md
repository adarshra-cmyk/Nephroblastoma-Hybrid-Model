---
title: Preprocessor
header-includes:
    <link href="styles.css" rel="stylesheet"/>
---

# Objective

The main objective of this script is to take the patient
miRNA data and drug information as input and modify the component
model initialization information. For example if certain miRNA
that directly influence mRNA in the networks, their initial
expression levels will be adjusted appropriately.

# Functions

The following functions are used to accomplish the above
objective

## Xml_to_Csv

**Function Signature**

```
def Xml_to_Csv(mirna_file):
```

**Summary(docstring)**

Writes a csv file from xml

**Input Parameters**

`mirna_file` (str) Name of the xml file containing miRNA data.

**Output Parameters**

`csvfile` (str) Name of the output csv file

**Output File**

`csvfile` Writes a csv file using the basename of the provided
xml file in the same location as the xml file.

**Local Parameters**

`root` (xml.etree.ElementTree) This an xml object that is
returned by parsing the provided xml file

`data` (str) The section containing the mirna expression data.

**Called Functions**

`change.Generate_Xml()` The function to parse a given xml file
and return the root xml object.

**Called by Functions**

`Top_Mirna()` If `Top_Mirna` gets an xml file as input it first
converts it to csv by calling this function.

**Description**

This function first calls `change.Generate_Xml()` to parse the
provided xml file and get the root element. Then it uses the
`find()` method of the `xml.etree.ElementTree` object to locate
and extract the mirna expression data. Then it writes this data
into a csv format and returns the name of the csv file.

**Example Run**

```
>>> import preprocessor as pr
>>> csvfile = pr.Xml_to_Csv("test_mirna_data.xml")
>>> csvfile
'test_mirna_data.csv'
>>> head("test_mirna_data.csv")

hsa-miR-507     -1.273868
hsa-miR-548d-5p 8.24556
hsa-miR-1976    -0.645146
hsa-miR-429     -1.03753
hsa-miR-1973    -5.73841
hsa-miR-1972    19.5356
hsa-miR-3065-3p -2.153585
hsa-miR-576-3p  -0.2749934
hsa-miR-181a*   -0.640422
```

## Top_Mirna

**Function Signature**

```
def Top_Mirna(mirna_file, delim = '\t', top = 20):
```

**Input Parameters**

`mirna_file` (str) This is the minml or csv file containing the
patient miRNA data. An example of the data format for each is
shown below for minml and csv

```xml
<Data-Table>
	<Column position="1">
	<Name>ID_REF</Name>
	</Column>
	<Column position="2">
	<Name>VALUE</Name>
	<Description>quantile normalized intensity values for each comparison</Description>
	</Column>
<Internal-Data rows="1205">
hsa-miR-507	-1.273868
hsa-miR-548d-5p	8.24556
    </Internal-Data>
</Data-Table>
```

For the csv file we only have the data corresponding to the rows
of the `Internal-Data` section. The `Xml_to_Csv()` function
simply extracts the data corresponding to this section.

`delim` (str) This is the delimiter used in the data and is the
tab character by default.

`top` (int) How many miRNA to be selected based on a sorted list
of expression (in descending order). Default value is 20.

**Output Parameters**

`top_mirna` (list) List of the `top` miRNA names whose
expressions are significantly altered.

**Called Functions**

`Xml_to_Csv()` If the file specified by `mirna_file` is
determined to be xml then convert it to a csv file by calling
this function.

**Called by Function**

Called in the `main` section to get a list of top miRNA names.

**Description**

This function first determines the type of input file (xml or
csv) and then reads the file. It stores the contents of all lines
except the header and converts the expressions into `float`.

```python
if os.path.splitext(mirna_file)[-1] == ".xml":
	mirna_file = Xml_to_Csv(mirna_file)
with open(mirna_file) as fp:
	for line in fp:
		if linc == 0:
			linc += 1
			continue
		else:
			mirna, expr = line.split(delim)
			mirna_data[mirna] = float(expr)
			linc += 1
```

Then it sorts the dictionary and obtains the `top` miRNA
names. The first line sorts based on value and the second
line gets the name of the top miRNA.

```python
sorted_mirna_data = sorted(mirna_data.items(), key = lambda x: x[1], reverse = True)
top_mirna = [ key for key, value in sorted_mirna_data[:top] ]
```

It then returns the list `top_mirna` to the caller.

**Example Run**

```
>>> head("test_mirna_data.csv")
miRNA   Expression
hsa-miR-507     -2.406847
hsa-miR-548d-5p 10.6867
hsa-miR-1976    0.098908
hsa-miR-429     -1.956009
hsa-miR-1973    -5.26973
hsa-miR-1972    31.9151
hsa-miR-3065-3p -2.378628
hsa-miR-576-3p  -2.782147
hsa-miR-181a*   -1.977651
>>> top_mirna = pr.Top_Mirna("test_mirna_data.csv")
>>> top_mirna
['hsa-miR-4281', 'hsa-miR-451', 'hsa-miR-2861',
'hsa-miR-1225-5p', 'hsa-miR-1207-5p', 'hsa-miR-638',
'hsa-miR-1202', 'hsa-miR-3665', 'hsa-miR-3656', 'hsa-miR-1915',
'hsa-miR-3663-3p', 'hsa-miR-223', 'hsa-miR-574-5p',
'hsa-miR-4270', 'hsa-miR-320c', 'hsa-miR-16', 'hsa-miR-4327',
'hsa-miR-762', 'hsa-miR-150*', 'hsa-miR-3679-5p']
```

## Mirna_Targets

**Function Signature**

```
def Mirna_Targets(mirna_names, mirtarfile):
```

**Input Parameters**

`mirna_names` (list) A list of mirna names which are
differentially expressed in the patient

`mirtarfile` (str) The csv file containing list of all miRNA and
their target mRNA downloaded from miRTarBase. The format of the
data in this file is as shown below

```csv
miRTarBase ID,miRNA,Species (miRNA),Target Gene,Target Gene (Entrez Gene ID),Species (Target Gene),Experiments,Support Type,References (PMID)
MIRT000002,hsa-miR-20a-5p,Homo sapiens,HIF1A,3091,Homo sapiens,Luciferase reporter assay//Western blot//Northern blot//qRT-PCR,Functional MTI,18632605
MIRT000002,hsa-miR-20a-5p,Homo sapiens,HIF1A,3091,Homo sapiens,Luciferase reporter assay//qRT-PCR//Western blot,Functional MTI,23911400
MIRT000002,hsa-miR-20a-5p,Homo sapiens,HIF1A,3091,Homo sapiens,HITS-CLIP,Functional MTI (Weak),22473208
MIRT000006,hsa-miR-146a-5p,Homo sapiens,CXCR4,7852,Homo sapiens,qRT-PCR//Luciferase reporter assay//Western blot,Functional MTI,18568019
```

**Output Parameters**

`mirna_targets_uniq` (dict) The unique mRNA which are directly
influenced by provided miRNA list

**Description**

This function reads the main database csv file line by line and
compares the name of the miRNA with those provided in the
list. If present in the list it adds the name of the target gene
into the main dictionary.

After reading the file it converts the list of genes to a unique
set.

**Example Run**

```
>>> mirna_targets_uniq = pr.Mirna_Targets(top_mirna, "hsa_MTI.csv")
>>> for key, value in mirna_targets_uniq.items()[:5]:
...     print({ key : value[:5] })
... 
{'hsa-miR-3665': ['RNF11', 'SFTPB', 'FXYD1', 'MLEC', 'ZDHHC18']}
{'hsa-miR-3663-3p': ['DIRAS1', 'ANKRD13A', 'PCBD2', 'BBS5', 'SLC6A8']}
{'hsa-miR-4270': ['SND1', 'PCSK2', 'TSPAN11', 'PCSK4', 'DUSP28']}
{'hsa-miR-16': []}
{'hsa-miR-762': ['MED28', 'POM121C', 'DAO', 'ANKRD13B', 'HLA-B']}
```

## Direct_Mrna_Targets

**Function Signature**

```
def Direct_Mrna_Targets(species,mirna_targets):
```

**Input Parameters**

`species` (list) A list of names of species which are present in
the network (gene ids)

`mirna_targets` (dict) The unique miRNA target dictionary
obtained from the `Mirna_Targets()` function

**Output Parameters**

`target_list` (list) This is a list of those species in the
network which are directly influenced by the miRNA

**Local Parameters**

`direct_mrna_targets` (dict) This is the dictionary that contains
the list of target mRNA which are present in the list `species`
corresponding to different miRNA.

**Description**

This function maps the target of different miRNA into the species
that are present in the network. It then returns a list of unique
species as the target list.

## Copasi_Species

**Function Signature**

```
def Copasi_Species(Cpsfile, name_filter = r"[a-zA-Z0-9]+\Z", Speciesfile="Network_Species.json"):
```

**Summary**

This gets a list of simple species name (not complex of two or
more species) and writes their names in a json file

**Input Parameters**

`Cpsfile` (str) Name of the input copasi file

`name_filter` (str) A filter that specifies a regular expression
to match while filtering the species names. This picks only those
names which consists of simple letters and numerals

`Speciesfile` (str) Name of output file where the names will be
written.

**Output Parameters**

`species_word` (dict) This contains the species id and names
along with the compartments

**Example Run**

```
>>> species_word = pr.Copasi_Species("ChenBIOMD0000000019_ErbB-WT_orig_norules.cps", Speciesfile = "Network_Species_Temp.json")
Species Names written in file Network_Species_Temp.json, check and ensure correct gene IDs
>>> species_word
{'SHP': ['Shp', 'cytoplasm'], 'AKT': ['AKT', 'cytoplasm'], 'CPP':
['cPP', 'endosomal membrane'], 'EGF': ['EGF', 'medium'], 'ERK':
['ERK', 'cytoplasm'], 'RAF': ['Raf', 'cytoplasm'], 'PASE9T':
['Pase9t', 'cytoplasm'], 'ERBB4': ['ErbB4', 'endosomal
membrane'], 'PIP2': ['PIP2', 'cytoplasm'], 'GAP': ['GAP',
'cytoplasm'], 'SOS': ['Sos', 'cytoplasm'], 'PASE2': ['Pase2',
'cytoplasm'], 'PASE3': ['Pase3', 'cytoplasm'], 'PASE1': ['Pase1',
'cytoplasm'], 'PASE4': ['Pase4', 'cytoplasm'], 'SHP2': ['Shp2',
'cytoplasm'], 'ERBB2': ['ErbB2', 'endosomal membrane'], 'ERBB3':
['ErbB3', 'endosomal membrane'], 'ERBB1': ['ErbB1', 'plasma
membrane'], 'PIP3': ['PIP3', 'cytoplasm'], 'PI3K': ['PI3K',
'cytoplasm'], 'SHC': ['Shc', 'cytoplasm'], 'HRG': ['HRG',
'medium'], 'GAB1': ['Gab1', 'cytoplasm'], 'MEK': ['MEK',
'cytoplasm'], 'PDK1': ['PDK1', 'cytoplasm'], 'PTEN': ['PTEN',
'cytoplasm'], 'GRB2': ['Grb2', 'cytoplasm'], 'INH': ['Inh',
'medium']}
```

# Classes

## Drug

This class gets the affected nodes and the base value for
different drugs.

# Main

The script performs the following tasks:

1. Imports the model configuration from the master json file.
2. Preprocesses the miRNA file and gets the list of top mRNA
which are influenced by the differentially expressed miRNA and
modifies initial network configuration
3. Gets the drug information from the file and modifies the
target nodes in the networks
4. Writes the modified boolean network and the ode network in
separate files with corresponding patient id.

The specific parts of the code that performs the above functions
are explained below

## Reading Main Configuration File

Code Section

```python
Configfile = "../interface/Run_Info_New.json"
Networktempfile = "Network_Species_Temp.json"
boolean_changes = { "states" : {}, "bases" : {} }

#Read configuration information
with open(Configfile) as fp: Run_Info = json.load(fp)
suffix = "_%s" % Run_Info["run_id"]
mirna_target_file = "miRNA_Targets%s.json" % suffix
```

The `suffix` is set corresponding to unique patient pseudo
anonymized id.

## Preprocess miRNA data

Code

```python
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
```

The above code first tries to open the target miRNA file if the
preprocessing was already done before for patient with id
`Run_Info["run_id"]`. If this was not
done the file does not exist and the code corresponding to the
`except IOError` is run which calls the corresponding functions
to get a list of target miRNA and at the same time writes the
target json file so that it can be used the next time.

If the json file exists but is not readable for some reason then
the code confirms with the user if it is okay to overwrite the
file. Upon confirmation from the user the code gets the list of
target miRNA and overwrites the file.

## Change Boolean Model Initial States

Based on the list of direct mRNA targets in boolean network that
are influenced by the miRNA, the initial states are set. The list
of mRNA targets are obtained by calling
[`Direct_Mrna_Targets`](#direct_mrna_targets) function.

```python
target_mrna = Direct_Mrna_Targets(boolmodel["network"].keys(), mirna_targets)
for key in target_mrna:
	boolean_changes["states"][key] = 0
```

## ODE Initialization

Next the list of species in the ODE model is determined by
reading the corresponding Copasi file using
[`Copasi_Species()`](#copasi_species). Then the user needs to confirm that the
corresponding gene IDs are correct in the temporary file. After
this the [`Direct_Mrna_Targets()`](#direct_mrna_targets) function is again used to obtain
the direct targets corresponding to the miRNA.

```python
species_words, species_values = Copasi_Species(Run_Info["models"]["chenode"]["file"], Speciesfile = Networktempfile)
res = raw_input("Check file %s, type y to continue, q to quit: " % Networktempfile)
if res == 'q':
	quit()
with open("Network_Species_Temp.json") as fp: ode_network = json.load(fp)
species = ode_network.keys()
ode_network_direct = Direct_Mrna_Targets(species, mirna_targets)
ode_network_targets = [ value for key, value in ode_network.items() if key in ode_network_direct ]
```

## Drug Preprocessing

Next based on the drug information in the main configuration file
the affected nodes and base values in the Boolean models are
determined by instantiating `Drug` class and calling the
appropriate methods.

```python
for key, value in Run_Info["drug"].items():
	if value["status"] == "on":
		drug = Drugs(key, value)
		base, nodes = drug.calc_base(), drug.find_nodes()
		for key in nodes:
			boolean_changes["states"][key] = 1


boolmodel["changes"].update(boolean_changes)
```

## Program Output

Finally the modified configurations of the ODE and boolean
networks are written to appropriate files.
