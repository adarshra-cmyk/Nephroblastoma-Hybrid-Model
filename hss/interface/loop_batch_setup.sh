#!/bin/bash

module load anaconda3

drugs=("Control" "Dox" "Vincristine" "Actinomycin" "Dox_Vincristine" "Actinomycin_Vincristine" "Actinomycin_Dox_Vincristine")
radlevels=(0) # 5 10 15 20 25
patients=("Control" "4L3YB6" "5XIHQG" "6Z34IQ" "ECCOAH")
runname="lifer"

for p in ${patients[*]}; do
    for d in ${drugs[*]}; do
        conda run -n nephro python batch_setup.py Run_Info_"$runname"_"$p"_"$d".json
        # for r in ${radlevels[*]}; do
        #     conda run -n nephro python batch_setup.py Run_Info_"$runname"_"$p"_"$d"_Rad_"$r"Gy.json
        # done
    done
done
