#!/bin/bash
#PBS -l nodes=1:ppn=8,walltime=30:00:00
#PBS -j eo 
#PBS -q opterons

cd /home/lifer/nephroblastoma_hybrid_model/hss/interface
echo "Job started on `hostname` at `date`"
echo " "
#python combined_run.py Run_Info_"$1"_Control.json &> output_cr_4c.log
#python combined_run.py Run_Info_"$1"_Dox.json &> output_cr_4d.log
#python combined_run.py Run_Info_"$1"_Vincristine.json &> output_cr_4v.log
python combined_run.py Run_Info_"$1".json &> output_ss_"$1".log
echo "Job Ended on `hostname` at `date`"
echo " "


