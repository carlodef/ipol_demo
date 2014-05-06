#!/bin/bash

#load params
. params

# compute the STATISTICS 
if [ "${ground_truth}" != "" ]; then 
    # exclude ground truth mask from the comparison 
    plambda ground_truth_mask.tif ground_truth.tif "x[0] 0 = inf y[0] if" > ground_truth_for_statistics.tif 
    # exclude filtered pixels from the computed disparity maps 
#    plambda out_filt.tif out_disp.tif "x[0] 0 = nan y[0] if" > out_disp_for_statistics.tif 
#    plambda filt_std_bm.tif disp_std_bm.tif "x[0] 0 = nan y[0] if" > disp_std_bm_for_statistics.tif 

    # compute the statistics
    disp_statistics disp_sgm.tif ground_truth_for_statistics.tif 1 > statistics.txt 
fi 
