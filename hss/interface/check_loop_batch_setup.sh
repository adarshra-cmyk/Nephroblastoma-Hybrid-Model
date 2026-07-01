#!/bin/bash

drugs=("Control" "Actinomycin" "Dox" "Vincristine" "Actinomycin_Dox" "Dox_Vincristine" "Actinomycin_Vincristine" "Actinomycin_Dox_Vincristine")
radlevels=(5 10 15 20 25)
patients=("4L3YB6" "5XIHQG" "6Z34IQ" "ECCOAH")

for p in  ${patients[*]}; do
    for d in ${drugs[*]}; do
        echo "$p"_"$d"
        #ls -hl Model_Data_lifer_"$p"_"$d"* | wc -l
        python batch_setup.py Run_Info_lifer_"$p"_"$d".json &>> lifer_"$p"_"$d".log &
        for r in ${radlevels[*]}; do
            echo "$p"_"$d"_Rad_"$r"Gy.json
            #ls -hl Model_Data_lifer_"$p"_"$d"_Rad_"$r"Gy* | wc -l
            python batch_setup.py Run_Info_lifer_"$p"_"$d"_Rad_"$r"Gy.json &>> "$p"_"$d"_Rad_"$r"Gy.log & 
        done
    done
done
