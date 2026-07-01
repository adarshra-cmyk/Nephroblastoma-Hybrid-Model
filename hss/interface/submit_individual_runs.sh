#!/bin/bash

cd /home/lifer/nephroblastoma_hybrid_model/hss/interface

qsub -N 4c -F lifer_4L3YB6_Control single_submit_combined_runs.sh
qsub -N 5c -F lifer_5XIHQG_Control single_submit_combined_runs.sh
qsub -N 6c -F lifer_6Z34IQ_Control single_submit_combined_runs.sh
qsub -N ec -F lifer_ECCOAH_Control single_submit_combined_runs.sh
qsub -N s4c -F lifer_short_4L3YB6_Control single_submit_combined_runs.sh
qsub -N s5c -F lifer_short_5XIHQG_Control single_submit_combined_runs.sh
qsub -N s6c -F lifer_short_6Z34IQ_Control single_submit_combined_runs.sh
qsub -N sec -F lifer_short_ECCOAH_Control single_submit_combined_runs.sh

qsub -N 4d -F lifer_4L3YB6_Dox single_submit_combined_runs.sh
qsub -N 5d -F lifer_5XIHQG_Dox single_submit_combined_runs.sh
qsub -N 6d -F lifer_6Z34IQ_Dox single_submit_combined_runs.sh
qsub -N ed -F lifer_ECCOAH_Dox single_submit_combined_runs.sh
qsub -N s4d -F lifer_short_4L3YB6_Dox single_submit_combined_runs.sh
qsub -N s5d -F lifer_short_5XIHQG_Dox single_submit_combined_runs.sh
qsub -N s6d -F lifer_short_6Z34IQ_Dox single_submit_combined_runs.sh
qsub -N ssed -F lifer_short_ECCOAH_Dox single_submit_combined_runs.sh

qsub -N 4dv -F lifer_4L3YB6_Dox_Vincristine single_submit_combined_runs.sh
qsub -N 5dv -F lifer_5XIHQG_Dox_Vincristine single_submit_combined_runs.sh
qsub -N 6dv -F lifer_6Z34IQ_Dox_Vincristine single_submit_combined_runs.sh
qsub -N edv -F lifer_ECCOAH_Dox_Vincristine single_submit_combined_runs.sh
qsub -N s4dv -F lifer_short_4L3YB6_Dox_Vincristine single_submit_combined_runs.sh
qsub -N s5dv -F lifer_short_5XIHQG_Dox_Vincristine single_submit_combined_runs.sh
qsub -N s6dv -F lifer_short_6Z34IQ_Dox_Vincristine single_submit_combined_runs.sh
qsub -N sedv -F lifer_short_ECCOAH_Dox_Vincristine single_submit_combined_runs.sh

qsub -N 4v -F lifer_4L3YB6_Vincristine single_submit_combined_runs.sh
qsub -N 5v -F lifer_5XIHQG_Vincristine single_submit_combined_runs.sh
qsub -N 6v -F lifer_6Z34IQ_Vincristine single_submit_combined_runs.sh
qsub -N ev -F lifer_ECCOAH_Vincristine single_submit_combined_runs.sh
qsub -N s4v -F lifer_short_4L3YB6_Vincristine single_submit_combined_runs.sh
qsub -N s5v -F lifer_short_5XIHQG_Vincristine single_submit_combined_runs.sh
qsub -N s6v -F lifer_short_6Z34IQ_Vincristine single_submit_combined_runs.sh
qsub -N sev -F lifer_short_ECCOAH_Vincristine single_submit_combined_runs.sh
