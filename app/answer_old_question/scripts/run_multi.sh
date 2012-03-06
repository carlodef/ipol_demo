#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin

#load params
. params

# Provided arguments:
# $1 : tilt parameter 
# $2 : disp_min current
# $3 : disp_max current

# 1. Do the block-matching: this is the time-consuming step
echo "stereoSSD-mean -w $win_w -h $win_h -r $2 -R $3 input_1.png input_0_t$1.png disp_t$1.tif cost_t$1.tif dispR_t$1.tif costR_t$1.tif" 
stereoSSD-mean -w $win_w -h $win_h -r $2 -R $3 input_1.png input_0_t$1.png disp_t$1.tif cost_t$1.tif dispR_t$1.tif costR_t$1.tif 

# 2. Filtering
echo "stereoLRRL disp_t$1.tif dispR_t$1.tif filt_t$1.png 1"
stereoLRRL disp_t$1.tif dispR_t$1.tif filt_t$1.tif 1

echo "save_png_mask.sh filt_t$1.tif filt_t$1.png"
save_png_mask.sh filt_t$1.tif filt_t$1.png

# 3. Correct disparity values according to tilt
echo "correction_disp.sh $1"
correction_disp.sh $1

# 4. Compute RMSE
echo "disp_statistics disp_t$1_corrected.tif gt.tif 1 > stat_t$1.txt"
disp_statistics disp_t$1_corrected.tif gt.tif 1 > stat_t$1.txt

