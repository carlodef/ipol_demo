#!/bin/bash

#load params
. params

# compute the STATISTICS 
if [ "${ground_truth}" != "" ]; then 
    # exclude ground truth mask from the comparison 
    plambda ground_truth_mask.tif ground_truth.tif "x[0] 0 = inf y[0] if" > ground_truth_for_statistics.tif 
    disp_statistics out_disp.tif ground_truth_for_statistics.tif 1 > statistics.txt 
    disp_statistics disp_std_bm.tif ground_truth_for_statistics.tif 1 >> statistics.txt 
fi 
