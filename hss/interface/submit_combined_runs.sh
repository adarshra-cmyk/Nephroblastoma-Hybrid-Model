#!/bin/bash
#PBS -l nodes=1:ppn=8,walltime=80:00:00
#PBS -j eo 
#PBS -q opterons
#PBS -N Combined_Run_lifer

cd /home/lifer/nephroblastoma_hybrid_model/hss/interface
echo "Job started on `hostname` at `date`"
echo " "
python combined_run.py Run_Info_lifer_4L3YB6_Control.json &> output_cr_4c.log
python combined_run.py Run_Info_lifer_4L3YB6_Dox.json &> output_cr_4d.log
python combined_run.py Run_Info_lifer_4L3YB6_Vincristine.json &> output_cr_4v.log
python combined_run.py Run_Info_lifer_4L3YB6_Dox_Vincristine.json &> output_cr_4dv.log

python combined_run.py Run_Info_lifer_5XIHQG_Control.json &> output_cr_5c.log
python combined_run.py Run_Info_lifer_5XIHQG_Dox.json &> output_cr_5d.log
python combined_run.py Run_Info_lifer_5XIHQG_Vincristine.json &> output_cr_5v.log
python combined_run.py Run_Info_lifer_5XIHQG_Dox_Vincristine.json &> output_cr_5dv.log

python combined_run.py Run_Info_lifer_6Z34IQ_Control.json &> output_cr_6c.log
python combined_run.py Run_Info_lifer_6Z34IQ_Dox.json &> output_cr_6d.log
python combined_run.py Run_Info_lifer_6Z34IQ_Vincristine.json &> output_cr_6v.log
python combined_run.py Run_Info_lifer_6Z34IQ_Dox_Vincristine.json &> output_cr_6dv.log

python combined_run.py Run_Info_lifer_ECCOAH_Control.json &> output_cr_ec.log
python combined_run.py Run_Info_lifer_ECCOAH_Dox.json &> output_cr_ed.log
python combined_run.py Run_Info_lifer_ECCOAH_Vincristine.json &> output_cr_ev.log
python combined_run.py Run_Info_lifer_ECCOAH_Dox_Vincristine.json &> output_cr_edv.log

echo "Job Ended on `hostname` at `date`"
echo " "


