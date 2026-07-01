#!/usr/bin/env python

import os,re,subprocess,shutil,sys,glob
import json, shelve,multiprocessing,platform, pickle
import itertools, collections, copy, errno, random
from random import choice
from optparse import OptionParser
#from interface import CopasiState
#from Truth_Table import GenerateTable, Calculate_State
#from interpret_link import Target_mRNA_List_Csv
#from ordereddict import OrderedDict
#from mwe_base import Combined_Run
#from multiprocessing import Pool
#from mwe_collector import Collect_Data
from pprint import pprint


def DrugTargets(drug_name,drug_info):
    """
    This function takes data related to drug dosage and
    returns the list of targets in the current network
    for which the initial concentration need to be
    adjusted
    """

    nodes = []

    if drug_name == "Dox" or drug_name == "Actinomycin":

        #Calculate the atm base level
        KD = drug_info["constants"][0]
        coeff = drug_info["constants"][1]
        atm_base = int(round(3/(((KD/drug_info["dosage"])**coeff) + 1) - 1))

        #Change influenced node status based on threshold
        if drug_info["dosage"] > drug_info["threshold"]:
            nodes = nodes + drug_info["influenced_nodes"]

        return atm_base, nodes

    if drug_name == "Vincristine":
        #Check drug threshold value
        cdk1_base = 1
        if drug_info["dosage"] > drug_info["threshold"]:
            nodes = nodes + drug_info["influenced_nodes"]

        return cdk1_base,nodes

def MirnaODE(input_fn,shortcuts,genes):

    """
    This function takes the dictionary of mRNA names
        and changes the corresponding species in ODE model
        by a fixed percentage
    """

    sim = CopasiState(input_fn)
    sim.source_script(shortcuts)

    #Custom expression to remove brackets from an expression
    debracket = lambda x : re.findall('\[([^\]]+)\]',x)
    custom = lambda x : re.findall('^([^\[]+)', x)
    catalog = []
    values = []
    change_list = []
    for elem in sim.get('init_species'):

        species_comp = dict([(key,val[0]) for key,val in [(custom(i.split('=')[1])[0], debracket(i.split('=')[1])) for i in elem.attrib['cn'].split(',')] if val!=[]])
        catalog.append(species_comp)
        values.append(dict({species_comp['Metabolites']:elem.attrib['value']}))

    catalog = [(i['Metabolites'],i['Compartments'],j[i['Metabolites']]) for i,j in zip(catalog,values)]

    for index in [ii for ii,i in enumerate(catalog) if i[0] in genes]:
        sim.change('init_species','%s@%s'%catalog[index][:2],value=float(catalog[index][2])*0.75)
        change_list.append(catalog[index][0])

        sim.write(input_fn,override=True)

    return change_list

def Calculate_Ckr(cell_kill_ratio, drug_combination):
    """
    Calculates the adjusted CKR for the patient
    using a specified drug combination
    """
    Lit_CKR = {"Doxorubicin": 0.45, "Vincristine" : 0.28, "Actinomycin" : 0.4}
    drug_contribution = lambda x : 1 - (Lit_CKR[x] if drug_combination[x] else 0.0)
    Adj_Lit_CKR = 1 - drug_contribution("Doxorubicin")*drug_contribution("Vincristine")*drug_contribution("Actinomycin")
    Adj_CKR = 1 - (1 - Adj_Lit_CKR)**cell_kill_ratio

    return Adj_CKR

def Demo_Pre():

    with open("Cell_Fate_Patients.json") as fp: Patient_Data = json.load(fp)
    if options.patient_id not in Patient_Data.keys():
        raise Exception('Precomputed results not available for provided patient id, please select one from {0}'.format(','.join(Patient_Data.keys())))    
    model_input = 'Model_Input_DEMO.json'
    copasi_orig_fn = 'ChenBIOMD0000000019_ErbB-WT_orig_DEMO.cps'
    print "This is a demo version of the model and uses precomputed results"
    print "Please run the full version of the model to obtain new results for a specific use case"

    return model_input, copasi_orig_fn, Patient_Data
    
def Demo_Run():
    """
    Searches precomputed results for given
    patient and prints them
    """
    patid = options.patient_id

    Drug_Sign = lambda x : "{0}".format("+" if x else "-")
    drug_combination = "V{0},D{1},A{2}".format(Drug_Sign(options.Vinc),Drug_Sign(options.Dox),Drug_Sign(options.Act))
    drug_dict = { "Vincristine" : options.Vinc, "Doxorubicin" : options.Dox, "Actinomycin" : options.Act }
    drug_names = ' + '.join([key for key in drug_dict if drug_dict[key]])

    try:
        Mean_Cell_Fates = Patient_Data[patid]["cell_fate_mean"][drug_combination]
        if "V-,D-,A-" in Patient_Data[patid]["cell_fate_mean"].keys():
            Mean_Cell_Fates_Control = Patient_Data[patid]["cell_fate_mean"]["V-,D-,A-"]
        else:
            Mean_Cell_Fates_Control = Patient_Data[patid]["cell_fate_mean"]["V+,D-,A-"]
    except KeyError:
        print "Specified drug combinations {0} not used for patient {1}".format(drug_names, patid)
        return

    cell_kill_ratio = float(Mean_Cell_Fates["cell_death"])/float(Mean_Cell_Fates_Control["cell_death"])
    Adj_CKR = Calculate_Ckr(cell_kill_ratio, drug_dict)

    print 'Cell Fate Probabilities from precomputed data for patient {}:'.format(patid)
    print 'Selected drug combination: {}'.format(drug_names)
    print 'Cell Kill = {:.2f}, Cell Proliferation = {:.2f}, Cell Senescence = {:.2f}'.format(float(Mean_Cell_Fates['cell_death']),float(Mean_Cell_Fates['cell_growth']),float(Mean_Cell_Fates['cell_senescence']))
    print 'Adjusted CKR = {:.2f}'.format(Adj_CKR)
    with open(os.path.join(output_data,'ckr_total'),'w') as fp: fp.write('%.2f'%Adj_CKR)

    return Adj_CKR

def Cmdline_Process():
    """
    Returns a suitably initialized parser
    """
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.set_defaults(
        mirt_fn = "hsa_MTI.csv", Dox=False,
        parallel_run=False, no_of_cores=0,
        reinitialize_ode = False, demo=False,
        Act=False, Vinc=False, patient_id='5XIHQGQZ2GDYMITS5KON',
        mirna_input="mirna_data.csv", output_dirname="Output_Data")


    #Modify each variable name below as object.varname in subsequent code
    parser.add_option("-m", "--mirna-file", dest="mirna_input", help="[REQUIRED]:Micro RNA expression data for individual patient in minML format")

    parser.add_option("-o", "--output-dirname", dest="output_dirname", help="Full or relative(w.r.t. model folder) pathname to the output directory")
    parser.add_option("-I", "--patient-id", dest="patient_id", help="Anonymized id of the selected patient, required for for demo run")

    parser.add_option("-M", "--mirtar-file", dest="mirt_fn", help="Name of the mirtarbase data file in csv format")

    parser.add_option("-D", "--Doxorubicin-On", action="store_true", dest="Dox", help="Set whether Doxorubicin is above IC50 or not")
    parser.add_option("-A", "--Actinomycin-On", action="store_true", dest="Act", help="Set whether Actinomycin is above IC50")
    parser.add_option("-V", "--Vincristine-On", action="store_true", dest="Vinc", help="Set whether Actinomycin is above IC50")
    parser.add_option("-p", "--parallel-run", action="store_true", dest="parallel_run", help="Run program in parallel for different initial conditions, default number of cores is determined by program from available ones")
    parser.add_option("-n", "--no-of-cores", dest="no_of_cores", help="Provide the number of compute cores, by default program determines from available cores")
    parser.add_option("-r", "--reinitialize-ode", action="store_true", dest="reinitialize_ode", help="Specify whether or not to reinitialize the ODE module at every time step of the Boolean(DEFAULT - False)")
    parser.add_option("-d", "--demo-run", action="store_true", dest="demo", help="Run the demo version with precomputed results")

    return parser

if __name__ == '__main__':

    #Main program
    src = os.getcwd()
    os.chdir(sys.path[0])

    parser = Cmdline_Process()
    (options, args) = parser.parse_args()

    if 0:
        with open("Pat_Mirna_Dict.json") as fp: Pat_Mirna = json.load(fp)
        if options.patient_id != "Control" and options.patient_id not in Pat_Mirna.keys():
            raise Exception("No miRNA data found for patient {0}".format(patid))

        #Check required files
        if options.demo:
            model_input, copasi_orig_fn, Patient_Data = Demo_Pre(options)
        else:
            model_input = 'Model_Input.json'
            copasi_orig_fn = 'ChenBIOMD0000000019_ErbB-WT_orig_norules.cps'
        # Uncomment the two lines below if the mirna file is coming externally
        #if not options.mirna_input:
        #    parser.error('[REQUIRED]:Micro RNA expression data for individual patient in minML format')

        #------------------------------------------------
        #End of command line processing

        #Get system architecture and use appropriate copasi file
        if platform.architecture()[0] == '64bit':
            copasi_executable = 'Copasi_Executables/64_Bit/CopasiSE'
        if platform.architecture()[0] == '32bit':
            copasi_executable = 'Copasi_Executables/32_Bit/CopasiSE'

        #Get input filename and check existence
        #-----------------------------------------------
        if options.patient_id != "Control":
            with open("mirna_data.csv","w") as fp: fp.write("mirna,expr" + "\n" + "\n".join([','.join(map(str, list(elem))) for elem in Pat_Mirna[options.patient_id].items()]))
            pat_fn = "mirna_data.csv"

        parameter_fn = model_input

        output_data = options.output_dirname if os.path.isabs(options.output_dirname) else os.path.join(src, options.output_dirname)


        if not os.path.isfile(parameter_fn): raise Exception('[ERROR] invalid parameter file %s'%parameter_fn)
        #Cleanup working directory
        Create_Dir(output_data)
        input_fn=os.path.join(output_data, "MAPK_PI3K_Module_COPASI.cps")
        #Open the shelve file to store the data
        #Input_Data = shelve.open(os.path.join(output_data,'Input_Data.db'))
        Input_Data = {}
        ode_outfile = "Raw_time_course_Int"
        #------------------------------------------------

        #Data import and preprocessing Starts------------------------------------------
        #------------------------------------------------------------------------------

        with open(parameter_fn,'r') as fp: model_data = byteify(json.load(fp))
        sets = copy.deepcopy(model_data)


        #Provide proper extension to provided output filenames
        boolean_outfile = 'Raw_sync_Int.json'
        copasi_outfile = os.path.splitext(ode_outfile)[0] + '.csv'
        ode_ss_outfile = 'ODE_Steady_State.json'

        #Store a copy of the list of constrained nodes
        Constrained_Nodes = sets["Constrained_Nodes"][:]

        #Get and update the initial status of the boolean network
        #------------------------------------------------
        bool_node_states = {}

        for key,value in sets["p53_network"].items():
            bool_node_states[key] = value["initial_state"]

        #Get target mRNA names in Boolean and ODE modules
        if options.patient_id != "Control":
            miRNA_Targets_Bool, gene_miRNA, gene_all_unpacked = Target_mRNA_List_Csv(options.mirt_fn,pat_fn,sets["p53_network"])
            #Change miRNA target status
            for key in miRNA_Targets_Bool:
                bool_node_states[key] = 0
                Constrained_Nodes.append(key)

        shortcuts = '\n'.join(['path %s = %s'%(key,val) for key,val in sets['paths'].items()])
        #Copy input template copasi file
        copasi_fn = os.path.join(output_data, os.path.splitext(copasi_orig_fn)[0] + '_adjMirna.cps')
        shutil.copyfile(copasi_orig_fn, copasi_fn)

        #Call MirnaODE function to change the miRNA expression levels
        if options.patient_id != "Control":
            change_list = MirnaODE(copasi_fn, shortcuts, gene_all_unpacked)

        #Determine drug specific action using drug name/dosage info
        #------------------------------------------------
        #Check which drug is being used
        drug_list = []
        Chemo_Drug = copy.deepcopy(sets["Chemo_Drug"])

        #Set the drug status based on user input
        if options.Dox:
            Chemo_Drug["Dox"]["status"] = 'on'
        else:
            Chemo_Drug["Dox"]["status"] = 'off'

        if options.Act:
            Chemo_Drug["Actinomycin"]["status"] = 'on'
        else:
            Chemo_Drug["Actinomycin"]["status"] = 'off'

        if options.Vinc:
            Chemo_Drug["Vincristine"]["status"] = 'on'
        else:
            Chemo_Drug["Vincristine"]["status"] = 'off'
        for key,val in Chemo_Drug.items():
            if val["status"] == "on": drug_list.append(key)

        if "Dox" in drug_list:
            drug_info = Chemo_Drug["Dox"]
            atm_base,nodes = DrugTargets("Dox",drug_info)
            sets['p53_network']["ATM"]["base"] = atm_base
            for node in nodes:
                bool_node_states[node] = 1
                Constrained_Nodes.append(key)

        if "Actinomycin" in drug_list:
            drug_info = Chemo_Drug["Actinomycin"]
            atm_base,nodes = DrugTargets("Actinomycin",drug_info)
            sets['p53_network']["ATM"]["base"] = atm_base
            for node in nodes:
                bool_node_states[node] = 1
                Constrained_Nodes.append(key)

        if "Vincristine" in drug_list:
            drug_info = Chemo_Drug["Vincristine"]
            cdk1_base,nodes = DrugTargets("Vincristine",drug_info)
            sets['p53_network']["CDK1"]["base"] = cdk1_base
        #------------------------------------------------

        #Find the list of unconstrained nodes
        Unconstrained_Nodes = list(set(sets["p53_network"].keys()) - set(Constrained_Nodes))
        print "UPENN Nephroblastoma Hypermodel...."
        print "Created by: Dr. Ravi Radhakrishnan, Alok Ghosh"

        print 'ID of selected patient %s'%options.patient_id
        print "Drug status Vincristine = {0}, Actinomycin = {1}, Doxorubicin = {2}".format(options.Vinc, options.Act, options.Dox)
        #print Unconstrained_Nodes

        #Reorganize the data structure obtained from input file
        #------------------------------------------------
        sets['changes'] = dict((tuple(elem[0]),elem[1]) for elem in sets['changes'])
        sets['p53_network'] = dict(((key, value['base'],value['initial_state']),value['input_nodes']) for key, value in sets['p53_network'].items())

        Input_Data['sets'] = sets
        Input_Data['bool_node_states'] = bool_node_states
        Input_Data['copasi_fn'] = copasi_fn
        Input_Data['input_fn'] = input_fn
        Input_Data['copasi_outfile'] = copasi_outfile
        Input_Data['boolean_outfile'] = boolean_outfile
        Input_Data['ode_ss_outfile'] = ode_ss_outfile
        Input_Data['Unconstrained_Nodes'] = Unconstrained_Nodes
        Input_Data['model_data'] = model_data


        jobs = []

        init_iterator = [] #List containing the initial states
        if len(Unconstrained_Nodes) < 3:
            init_iterator = list(itertools.product([0, 1], repeat=len(Unconstrained_Nodes)))
        else:
            for _ in range(4):
                while True:
                    elem = [random.randint(0,1) for _ in range(len(Unconstrained_Nodes))]
                    if elem not in init_iterator: break
                init_iterator.append(elem)

        Input_Data['init_iterator'] = init_iterator
        #Input_Data.close()
        with open(os.path.join(output_data,'Input_Data.pkl'), "wb") as fp: pickle.dump(Input_Data, fp)


        #Start main loop over all set of initial conditions------------------------------
        #-------------------------------------------------------------------------------

        if options.parallel_run: #Setup parallel runs using multiprocessing

            #List of arguments for each initial state
            joblist = [(list(init_state),sets,bool_node_states,copasi_fn,input_fn,copasi_outfile,options.reinitialize_ode,output_data,copasi_executable) 
                    for init_state in init_iterator]
            if options.no_of_cores and options.no_of_cores <= multiprocessing.cpu_count():
                pool = Pool(options.no_of_cores)
            else:
                pool = Pool(multiprocessing.cpu_count())
            results = pool.map(Combined_Run,joblist)
            pool.close()
            pool.join()

        else: #Setup sequential processing

            for init_state in init_iterator:

                args = list(init_state),sets,bool_node_states,copasi_fn,input_fn,copasi_outfile,options.reinitialize_ode,output_data,copasi_executable
                Combined_Run(args)



        cell_kill_frac, cell_growth_frac, Unconstrained_Nodes = Collect_Data(options.patient_id, data_folder=output_data)
        #with open(os.path.join(output_data, 'cell_fates.csv'),'w') as fp: fp.write('cell_death,cell_growth,cell_senescence\n{0:.2f},{1:.2f},{2:.2f}'.format(cell_kill_frac,cell_growth_frac,1 - cell_kill_frac - cell_growth_frac))

        if options.demo:
            Adj_CKR = Demo_Run()
        else:
            Mean_Cell_Fates_Control = Patient_Data["Control"]["cell_fate_mean"]["V-,D-,A-"]
            cell_kill_ratio = float(cell_kill_frac)/Mean_Cell_Fates_Control
            drug_dict = { "Vincristine" : options.Vinc, "Doxorubicin" : options.Dox, "Actinomycin" : options.Act }
            drug_names = ' + '.join([key for key in drug_dict if drug_dict[key]])
            Adj_CKR = Calculate_Ckr(cell_kill_ratio, drug_dict)
            print 'Cell Fate Probabilities from precomputed data for patient {}:'.format(options.patient_id)
            print 'Selected drug combination: {}'.format(drug_names)
            print 'Cell Kill = {:.2f}, Cell Proliferation = {:.2f}, Cell Senescence = {:.2f}'.format(float(cell_kill_frac),float(cell_growth_frac),float(1 - cell_kill_frac - cell_growth_frac))
            print 'Adjusted CKR = {:.2f}'.format(Adj_CKR)

            with open(os.path.join(output_data,'ckr_total'),'w') as fp: fp.write('%.2f'%Adj_CKR)

        os.chdir(src)
        with open('ckr_total','w') as fp: fp.write('%.2f'%Adj_CKR)

