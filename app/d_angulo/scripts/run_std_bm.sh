#/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin:.

#load params
. params

# Subpixel parameter
export SUBPIXEL=$subpixel

# 1. Block-matching
stereoSSD-mean -w $win_w -h $win_h -r $min_disparity -R $max_disparity left_image.tif right_image.tif disp_std_bm.tif cost_std_bm.tif dispR_std_bm.tif costR_std_bm.tif 

# 2. Filtering
flatH left_image.tif filt_flat_std_bm.png $win_w
stereoLRRL2 disp_std_bm.tif dispR_std_bm.tif filt_LRRL_std_bm.png 1
intersection filt_LRRL_std_bm.png filt_flat_std_bm.png filt_std_bm.tif
save_png_mask.sh filt_std_bm.tif filt_std_bm.png

# 4. Generate png images for html display
save_png.sh disp_std_bm.tif disp_std_bm.png $min_disparity $max_disparity
save_png.sh cost_std_bm.tif cost_std_bm.png 0 100

