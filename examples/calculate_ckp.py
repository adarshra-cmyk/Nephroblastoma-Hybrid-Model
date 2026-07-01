#!/usr/bin/env python

import os,pdb,re,subprocess,shutil,sys,glob
import json, shelve,multiprocessing,platform
import itertools, collections, copy, errno, random
from random import choice
from optparse import OptionParser
from tools import call
from interface import CopasiState
from Truth_Table import GenerateTable, Calculate_State
from interpret_link import Target_mRNA_List
from ordereddict import OrderedDict
from mwe_base import Combined_Run
from multiprocessing import Pool
from mwe_collector import Collect_Data

def DrugTargets(drug_name,drug_info):
    """
    This function takes data related to drug dosage and
    returns the list of targets in the current network
    for which the initial concentration need to be
    adjusted
    """

    nodes = []

    if drug_name == "Dox":

        #Calculate the atm base level
        KD = drug_info["constants"][0]
        coeff = drug_info["constants"][1]
        atm_base = int(round(3/(((KD/drug_info["dosage"])**coeff) + 1) - 1))

        #Change influenced node status based on threshold
        if drug_info["dosage"] > drug_info["threshold"]:
            nodes = nodes + drug_info["influenced_nodes"]

        return atm_base, nodes

    if drug_name == "vincristine":
        #Check drug threshold value
        cdk1_base = 1
        if drug_info["dosage"] > drug_info["threshold"]:
            nodes = nodes + drug_info["influenced_nodes"]

        return cdk1_base,nodes

def MirnaODE(mirt_fn,pat_fn,input_fn,shortcuts,genes):

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

def MirnaBool(mirt_fn,pat_fn,p53_network):
    """
    This function takes the dictionary of miRNA names and
    returns the list of target mRNA for each module
    """
    #bool_list = [[key for key,value in i.items() if value == ["bool"]] for i in p53_network.values()]
    #miRNA_Targets_Name_Bool = set([j for i in bool_list for j in i])
    #miRNA_Targets_Bool = dict(zip(miRNA_Targets_Name_Bool, [1]*len(miRNA_Targets_Name_Bool)))

    #ode_list = [[key for key,value in i.items() if value[0] == "ode"] for i in p53_network.values()]
    #miRNA_Target_Name_Ode = set([j for i in ode_list for j in i])
    #miRNA_Targets_Ode = dict(zip(miRNA_Target_Name_Ode,[0.5]*len(miRNA_Target_Name_Ode)))

    miRNA_Targets_Bool, gene_miRNA, gene_all_unpacked = Target_mRNA_List(mirt_fn,pat_fn,p53_network)
    with open('miRNA_List.json','w') as fp: json.dump(gene_miRNA, fp)


    return miRNA_Targets_Bool

def byteify(input):
    """
    This function change json unicode output to ascii
    Source- http://stackoverflow.com/a/13105359
    """

    if isinstance(input, dict):
        return dict((byteify(key),byteify(value)) for key,value in input.iteritems())
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


if __name__ == '__main__':

    #---import parameters from parameter file

    #Initialize variables used in the code
    #------------------------------------------------

    src = os.getcwd()
    curr_dir = os.getenv('PWD')
    os.chdir(sys.path[0])

    #Counters for cell fates
    cell_death = cell_proliferation = cell_senescence = 0

    #Start of command line processing
    #------------------------------------------------

    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.set_defaults(
             mirt_fn = "hsa_MTI.csv", Dox=False, parallel_run=False, no_of_cores=0, reinitialize_ode = False, demo=False, primary_drug=False, mirna_source="tissue", plot_data=False, patient_id='5XIHQGQZ2GDYMITS5KON',mirna_input="miRNA_Data/CDR.Kidney.XX.XX.MINiML.5XIHQGQZ2GDYMITS5KON_tissue.xml", output_dirname="Output_Data")


    #Modify each variable name below as object.varname in subsequent code
    parser.add_option("-m", "--mirna-file", dest="mirna_input", help="[REQUIRED]:Micro RNA expression data for individual patient in minML format")

    parser.add_option("-s", "--mirna-source", dest="mirna_source", help="Source of mirna data(tissue or serum) default is tissue")
    parser.add_option("-o", "--output-dirname", dest="output_dirname", help="Full or relative(w.r.t. model folder) pathname to the output directory")
    parser.add_option("-I", "--patient-id", dest="patient_id", help="Anonymized id of the selected patient, required for for demo run. Results are available for following ids (select one): 4L3YB6HMJD3LK52ZVLCF, 5XIHQGQZ2GDYMITS5KON,6Z34IQAMEOQ2YZTU3SOE,ECCOAH3MWROQXV6BQOFH")

    parser.add_option("-M", "--mirtar-file", dest="mirt_fn", help="Name of the mirtarbase data file in csv format")

    parser.add_option("-D", "--Doxorubicin-On", action="store_true", dest="Dox", help="Set whether Doxorubicin is above IC50 or not")
    parser.add_option("-P", "--Primary-Drug", action="store_true", dest="primary_drug", help="Set whether the primary drug combination of vincristine and actinomycin is on or off")
    parser.add_option("-p", "--parallel-run", action="store_true", dest="parallel_run", help="Run program in parallel for different initial conditions, default number of cores is determined by program from available ones")
    parser.add_option("-n", "--no-of-cores", dest="no_of_cores", help="Provide the number of compute cores, by default program determines from available cores")
    parser.add_option("-r", "--reinitialize-ode", action="store_true", dest="reinitialize_ode", help="Specify whether or not to reinitialize the ODE module at every time step of the Boolean(DEFAULT - False)")
    parser.add_option("-d", "--demo-run", action="store_true", dest="demo", help="Run the demo version with precomputed results")
    parser.add_option("--plot-data", action="store_true", dest="plot_data", help="Specify if plots and report pdf will be generated from output data (requies additional python and external packages, see README)")

    (options, args) = parser.parse_args()

    #Check required files
    if options.demo:
        model_input = 'Model_Input_DEMO.json'
        copasi_orig_fn = 'ChenBIOMD0000000019_ErbB-WT_orig_DEMO.cps'
    else:
        model_input = 'Model_Input.json'
        copasi_orig_fn = 'ChenBIOMD0000000019_ErbB-WT_orig_norules.cps'
    if not options.mirna_input:
        parser.error('[REQUIRED]:Micro RNA expression data for individual patient in minML format')
    if options.patient_id not in ['4L3YB6HMJD3LK52ZVLCF', '5XIHQGQZ2GDYMITS5KON','6Z34IQAMEOQ2YZTU3SOE','ECCOAH3MWROQXV6BQOFH'] and options.demo:
        parser.error('Precomputed results not available for provided patient id, please select one from 4L3YB6HMJD3LK52ZVLCF, 5XIHQGQZ2GDYMITS5KON,6Z34IQAMEOQ2YZTU3SOE,ECCOAH3MWROQXV6BQOFH')

    #------------------------------------------------
    #End of command line processing

    #Get system architecture and use appropriate copasi file
    if platform.architecture()[0] == '64bit':
        copasi_executable = os.path.abspath('Copasi_Executables/64_Bit/CopasiSE')
    if platform.architecture()[0] == '32bit':
        copasi_executable = os.path.abspath('Copasi_Executables/32_Bit/CopasiSE')

    #Get input filename and check existence
    #-----------------------------------------------
    #pat_fn = 'miRNA_Data/' + os.path.basename(options.mirna_input)
    pat_fn = options.mirna_input if os.path.isabs(options.mirna_input) else os.path.join(curr_dir, options.mirna_input)
    parameter_fn = model_input

    output_data = options.output_dirname if os.path.isabs(options.output_dirname) else os.path.join(curr_dir, options.output_dirname)

    if not os.path.isfile(pat_fn): raise Exception('[ERROR] invalid mirna file %s'%pat_fn)

    if not os.path.isfile(parameter_fn): raise Exception('[ERROR] invalid parameter file %s'%parameter_fn)
    #Cleanup working directory
    try:
        os.makedirs(output_data)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(output_data): pass
        else: raise
    input_fn=os.path.join(output_data, "MAPK_PI3K_Module_COPASI.cps")
    #Open the shelve file to store the data
    Input_Data = shelve.open(os.path.join(output_data,'Input_Data.db'))
    ode_outfile = "Raw_time_course_Int"
    #------------------------------------------------

    #Data import and preprocessing Starts------------------------------------------
    #------------------------------------------------------------------------------

    with open(parameter_fn,'r') as fp: model_data = byteify(json.load(fp))

    #---custom unpacker
    sets = {}
    for key in model_data: sets[key] = model_data[key]

    #if options.Dox: sets['Dox'] = options.Dox


    #Provide proper extension to provided output filenames
    boolean_outfile = 'Raw_sync_Int.json'
    copasi_outfile = os.path.splitext(ode_outfile)[0] + '.csv'
    ode_ss_outfile = 'ODE_Steady_State.json'


    copasi_outfile_orig = str(copasi_outfile)


    #Add CDK1 and interface species into the list of constrained
    #nodes
    Constrained_Nodes = ['CDK1','ERK_PP','AKT_PP','Raf_P']

    #Get and update the initial status of the boolean network
    #------------------------------------------------
    bool_node_states = {}
    bool_node_states.update(dict((key,value["initial_state"]) for key,value in sets["p53_network"].items()))

    #Create lambda for getting the network state
    fingp_gen = lambda ordered_dict, cstrip = '[]', creplace = (', ',''): str ( [value for value in ordered_dict.values()] ).strip(cstrip).replace(*creplace)

    #Get target mRNA names in Boolean and ODE modules
    #------------------------------------------------
    miRNA_Targets_Bool, gene_miRNA, gene_all_unpacked = Target_mRNA_List(options.mirt_fn,pat_fn,sets["p53_network"])
    #Change miRNA target status
    for key in miRNA_Targets_Bool:
        bool_node_states[key] = 0
        Constrained_Nodes.append(key)

    shortcuts = '\n'.join(['path %s = %s'%(key,val) for key,val in sets['paths'].items()])
    #Copy input template copasi file
    copasi_fn = os.path.join(output_data, os.path.splitext(copasi_orig_fn)[0] + '_adjMirna.cps')
    shutil.copyfile(copasi_orig_fn, copasi_fn)

    #Call MirnaODE function to change the miRNA expression levels
    change_list = MirnaODE(options.mirt_fn, pat_fn, copasi_fn, shortcuts, gene_all_unpacked)

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

    if options.primary_drug:
        Chemo_Drug["vincristine"]["status"] = 'on'
    else:
        Chemo_Drug["vincristine"]["status"] = 'off'

    for key,val in Chemo_Drug.items():
        if val["status"] == "on": drug_list.append(key)

    if "Dox" in drug_list:
        drug_info = Chemo_Drug["Dox"]
        atm_base,nodes = DrugTargets("Dox",drug_info)
        sets['p53_network']["ATM"]["base"] = atm_base
        for node in nodes:
            bool_node_states[node] = 1
            Constrained_Nodes.append(key)

    if "vincristine" in drug_list:
        drug_info = Chemo_Drug["vincristine"]
        cdk1_base,nodes = DrugTargets("vincristine",drug_info)
        sets['p53_network']["CDK1"]["base"] = cdk1_base
    #------------------------------------------------

    #Find the list of unconstrained nodes
    Unconstrained_Nodes = list(set(sets["p53_network"].keys()) - set(Constrained_Nodes))
    print "UPENN Nephroblastoma Hypermodel...."
    print "Created by: Dr. Ravi Radhakrishnan, Alok Ghosh"

    if options.demo:
        print "This is a demo version of the model and uses precomputed results"
        print "Please run the full version of the model to obtain new results for a specific use case"
    print 'ID of selected patient %s'%options.patient_id
    print "Primary Drug (Vincristine + Actinomycin) = %s, Secondary Drug (Doxorubicin) = %s"%('ON' if options.primary_drug else 'OFF','ON' if options.Dox else 'OFF')
    print "Source of Micro RNA data= %s"%(options.mirna_source)
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


    jobs = []

    if options.demo:
        init_iterator = []
        if len(Unconstrained_Nodes) < 3:
            init_iterator = list(itertools.product([0, 1], repeat=len(Unconstrained_Nodes)))
        else:
            for _ in range(4):
                while True:
                    elem = [random.randint(0,1) for _ in range(len(Unconstrained_Nodes))]
                    if elem not in init_iterator: break
                init_iterator.append(elem)

        Input_Data['init_iterator'] = init_iterator
    else:
        init_iterator = list(itertools.product([0, 1], repeat=len(Unconstrained_Nodes)))
    Input_Data.close()


    #Start main loop over all set of initial conditions------------------------------
    #-------------------------------------------------------------------------------

    #---create an argument list for each initial condition
    if options.parallel_run:
        
        joblist = [(list(init_state),sets,bool_node_states,copasi_fn,input_fn,copasi_outfile,options.reinitialize_ode,output_data,copasi_executable) 
                for init_state in init_iterator]
        #---parallel loop over initial conditions
        #print "STARTING!!!!!!!!!"
        if options.no_of_cores:
            pool = Pool(options.no_of_cores)
        else:
            pool = Pool(multiprocessing.cpu_count())
        results = pool.map(Combined_Run,joblist)
        pool.close()
        pool.join()
        # watch echo "completed number db = "$(ls -all Output*.db | wc | awk '{print $1}')

    else:

        for init_state in init_iterator:
            
            args = list(init_state),sets,bool_node_states,copasi_fn,input_fn,copasi_outfile,options.reinitialize_ode,output_data,copasi_executable
            Combined_Run(args)







    #for files in glob.glob(os.path.splitext(input_fn)[0] + '*.cps'): os.remove(files)
    #for files in glob.glob(os.path.splitext(ode_outfile)[0] + '*.csv'): shutil.copyfile(files, os.path.join(output_data,files))
    #for files in glob.glob(os.path.splitext(ode_outfile)[0] + '*.csv'): os.remove(files)
    #for files in glob.glob('Output_Data' + '*.db'): shutil.copyfile(files, os.path.join(output_data,files))
    #for files in glob.glob('Output_Data' + '*.db'): os.remove(files)

    #Getting the precomputed cell kill ratios and probabilities for a demo run

    cell_kill_frac, cell_growth_frac,Unconstrained_Nodes = Collect_Data(data_folder=output_data)
    with open(os.path.join(output_data, 'cell_fates.csv'),'w') as fp: fp.write('cell_death,cell_growth,cell_senescence\n%f,%f,%f'%(cell_kill_frac,cell_growth_frac,1 - cell_kill_frac - cell_growth_frac))
    with open(os.path.join(output_data,'ckr_total'),'w') as fp: fp.write('%f'%cell_kill_frac)

    if options.demo:

        #Get list of directories under precomputed data
        result_directories = os.listdir('Precomputed_Results')

        for filename in result_directories:
            if options.patient_id in filename:
                dir_name = filename 
                break

        with open('Precomputed_Results/' + dir_name + '/' + 'Cell_Fate_Mean.csv', 'r') as fp: cell_fate_mean = fp.read().splitlines()
        with open('Precomputed_Results/' + dir_name + '/' + 'Cell_Fate_Ratio.csv', 'r') as fp: cell_fate_ratio = fp.read().splitlines()


        mean_param_names = cell_fate_mean[0].split(',')
        mean_param_values = [lines.split(',') for lines in cell_fate_mean[1:]]

        if options.Dox and options.primary_drug:
            drug_dosage = '(D+;V+;A+)'
        if not options.Dox and options.primary_drug:
            drug_dosage = '(D-;V+;A+)'
        if not options.Dox and not options.primary_drug:
            drug_dosage = '(D-;V-;A-)'

        index_count = 0

        for index, mean_param_elem in enumerate(mean_param_values):
            if drug_dosage in mean_param_elem and options.mirna_source in mean_param_elem:
                cell_fate_list = mean_param_elem
                break
            index_count = index_count + 1
        if index_count == len(mean_param_values):
            raise Exception('No precomputed data found for given mirna source and drug combination, please select some other combination') 

        cell_fate_dict = dict(zip(mean_param_names, cell_fate_list))
        
        print 'Cell fate probabilities from precomputed data for patient {}: Cell kill = {}, Cell Proliferation = {}, Cell Senescence = {}'.format(options.patient_id,cell_fate_dict['Cell-Death-Mean'],cell_fate_dict['Cell-Growth-Mean'],cell_fate_dict['Cell-Senescence-Mean'])
        with open(os.path.join(output_data, 'cell_fate_prob.csv'),'w') as fp: fp.write('cell_death,cell_growth,cell_senescence\n{},{},{}'.format(cell_fate_dict['Cell-Death-Mean'],cell_fate_dict['Cell-Growth-Mean'],cell_fate_dict['Cell-Senescence-Mean']))
        with open(os.path.join(output_data, 'ckr_prob'),'w') as fp: fp.write('%f'%float(cell_fate_dict['Cell-Death-Mean']))


        ratio_param_names = cell_fate_ratio[0].split(',')
        ratio_param_values = [lines.split(',') for lines in cell_fate_ratio[1:]]

        if options.Dox and options.primary_drug:
            drug_dosage = '(D+;V+;A+)'
        if not options.Dox and options.primary_drug:
            drug_dosage = '(D-;V+;A+)'
        if not options.Dox and not options.primary_drug:
            drug_dosage = '(D-;V-;A-)'

        for index, ratio_param_elem in enumerate(ratio_param_values):
            if drug_dosage in ratio_param_elem:
                cell_fate_list = ratio_param_elem
                break
        cell_fate_dict = dict(zip(ratio_param_names, cell_fate_list))
        
        print 'Cell fate ratios (with respect to consensus patient) from precomputed data for patient {}: Cell kill = {}, Cell Proliferation = {}, Cell Senescence = {}'.format(options.patient_id,cell_fate_dict['Cell-Death-Ratio'],cell_fate_dict['Cell-Growth-Ratio'],cell_fate_dict['Cell-Senescence-Ratio'])
        with open(os.path.join(output_data, 'cell_fate_ratio.csv'),'w') as fp: fp.write('cell_death,cell_growth,cell_senescence\n{},{},{}'.format(cell_fate_dict['Cell-Death-Ratio'],cell_fate_dict['Cell-Growth-Ratio'],cell_fate_dict['Cell-Senescence-Ratio']))
        with open(os.path.join(output_data, 'ckr_ratio'),'w') as fp: fp.write('%f'%float(cell_fate_dict['Cell-Death-Ratio']))

    else:
        with open('Precomputed_Results/Consensus_Patient/Cell_Fate_Mean.csv', 'r') as fp: cell_fate_mean = fp.read().splitlines()

        mean_param_names = cell_fate_mean[0].split(',')
        mean_param_values = [lines.split(',') for lines in cell_fate_mean[1:]][0]
        cell_fate_dict = dict(zip(mean_param_names, mean_param_values))
        
        with open(os.path.join(output_data, 'cell_fate_ratio.csv'),'w') as fp: fp.write('cell_death,cell_growth,cell_senescence\n{},{},{}'.format(cell_kill_frac/float(cell_fate_dict['Cell-Death-Mean']),cell_growth_frac/float(cell_fate_dict['Cell-Growth-Mean']),(1 - cell_kill_frac - cell_growth_frac)/float(cell_fate_dict['Cell-Senescence-Mean'])))
        with open(os.path.join(output_data, 'ckr_ratio'),'w') as fp: fp.write('%f'%(cell_kill_frac/float(cell_fate_dict['Cell-Death-Mean'])))
        print 'Calculated cell fate probabilities for patient {}: Cell kill = {}, Cell Proliferation = {}, Cell Senescence = {}'.format(options.patient_id,cell_kill_frac,cell_growth_frac,1 - cell_kill_frac - cell_growth_frac)
        print 'Calculated cell fate ratios (with respect to consensus patient) for patient {}: Cell kill = {}, Cell Proliferation = {}, Cell Senescence = {}'.format(options.patient_id,cell_kill_frac/float(cell_fate_dict['Cell-Death-Mean']),cell_growth_frac/float(cell_fate_dict['Cell-Growth-Mean']),(1 - cell_kill_frac - cell_growth_frac)/float(cell_fate_dict['Cell-Senescence-Mean']))


    #Data plotting
    if options.plot_data:
        from Plot_Data import Generate_Plot, Compile_Report
        latex_string = ['\\subsection{Detailed Results}\n']
        input_filename = 'Input_Data.db'
        image_list, init_iterator, Unconstrained_Nodes = Generate_Plot(src, input_filename)
        lines = Compile_Report(image_list, input_filename, src, init_iterator, Unconstrained_Nodes) # Function to generate compiled latex document
        latex_string.append(lines)
        with open('Result_per_loop.tex','w') as fp: fp.write("".join(latex_string))
        shutil.move(os.path.join(src,'Result_per_loop.tex'),os.path.join(src, 'Report/Result_per_loop.tex'))
        shutil.copyfile('Precomputed_Results/' + dir_name + '/' + 'Cell_Fate_BarPlot.png', 'Report/')

        os.chdir('Report')

        try:
            latex_proc = subprocess.call(['pdflatex','-interaction', 'nonstopmode', 'Report.tex'])
        except OSError:
            print 'Latex not installed in the system no pdfs were generated'
            latex_proc = 1

        if latex_proc == 0:
            print 'Reports pdf generated within the Report folder' 
        else:
            print 'Pdf compilation failed please check Report.log logfile in Report folder for more details'

        os.chdir('..')

    os.chdir(src)
