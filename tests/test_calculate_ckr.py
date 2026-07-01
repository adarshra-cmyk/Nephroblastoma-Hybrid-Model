#!/usr/bin/env python

import unittest
from examples.calculate_ckr import Cmdline_Process
from optparse import OptionParser, make_option

testoptions = {
    'Act': {"opts" : ["-A","--Actinomycin-On"], "action" : "store_true", "help" : "Set whether Actinomycin is above IC50" },
    'Dox': {"opts" : ["-D","--Doxorubicin-On"], "action" : "store_true", "help" : "Set whether Doxorubicin is above IC50 or not" },
    'Vinc': {"opts" : ["-V", "--Vincristine-On"], "action" : "store_true", "help" : "Set whether Actinomycin is above IC50" },
    'demo': {"opts" : ["-d", "--demo-run"],"action" : "store_true","help" : "Run the demo version with precomputed results"},
    'mirna_input': {"opts" : ["-m", "--mirna-file"],"help" : "[REQUIRED]:Micro RNA expression data for individual patient in minML format"},
    'mirt_fn': {"opts" : ["-M", "--mirtar-file"],"help" : "Name of the mirtarbase data file in csv format"},
    'no_of_cores': {"opts" : ["-n", "--no-of-cores"],"help" : "Provide the number of compute cores, by default program determines from available cores"},
    'output_dirname': {"opts" : ["-o", "--output-dirname"],"help" : "Full or relative(w.r.t. model folder) pathname to the output directory"},
    'parallel_run': {"opts" : ["-p", "--parallel-run"],"action" : "store_true","help" : "Run program in parallel for different initial conditions, default number of cores is determined by program from available ones"},
    'patient_id': {"opts" : ["-I", "--patient-id"],"help" : "Anonymized id of the selected patient, required for for demo run"},
    'reinitialize_ode': {"opts" : ["-r", "--reinitialize-ode"],"action" : "store_true","help" : "Specify whether or not to reinitialize the ODE module at every time step of the Boolean(DEFAULT - False)"}
}

class TestSweeps(unittest.TestCase):

    def test_Cmdline_Process(self):
        """
        Tests the command line processing
        function
        """
        testdefaults = {'Act': False, 'Dox': False, 'Vinc': False, 'demo': False, 'mirna_input': 'mirna_data.csv', 'mirt_fn': 'hsa_MTI.csv', 'no_of_cores': 0, 'output_dirname': 'Output_Data', 'parallel_run': False, 'patient_id': '5XIHQGQZ2GDYMITS5KON', 'reinitialize_ode': False}
        testoptionlist = []
        short_options = ["-m","-o","-I","-M","-D","-A","-V","-p","-n","-r","-d"]
        long_options = ["--mirna-file","--output-dirname","--patient-id","--mirtar-file","--Doxorubicin-On","--Actinomycin-On","--Vincristine-On","--parallel-run","--no-of-cores","--reinitialize-ode","--demo-run"]
        values = ["hsa_MTI.csv","Output_Data","5XIHQGQZ2GDYMITS5KON", "mirna_data.csv", False, True, False, False, 0, True, False]
        for key in testoptions:
            opts = testoptions[key].pop("opts")
            testoptions[key]["dest"] = key
            testoptionlist.append(make_option(*opts, **testoptions[key])) 
        parser = Cmdline_Process()
        test_parser = OptionParser(option_list = testoptionlist)
        test_parser.set_defaults(**testdefaults)
        #testcmd = sum(zip(short_options, values), ())
        testcmd = []
        for opt, val in zip(short_options, values):
            if not isinstance(val, bool):
                testcmd.extend([opt, val])
            else:
                testcmd.append(opt)
        (options, args) = parser.parse_args(list(testcmd))
        (test_options, test_args) = test_parser.parse_args(list(testcmd))
        self.assertEqual(eval(options.__str__()), eval(test_options.__str__()))
        


if __name__ == '__main__':
    unittest.main()
