#/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin

#load params
. params

# Subpixel parameter
export SUBPIXEL=$subpixel

# Provided arguments:
# $1 : tilt parameter 
# $2 : shear parameter
# $3 : disp_min current
# $4 : disp_max current


# 1. Do the block-matching: this is the time-consuming step
echo "stereoSSD-mean -w $win_w -h $win_h -r $3 -R $4 left_image.tif right_image_t$1_s$2.tif disp_t$1_s$2.tif cost_t$1_s$2.tif dispR_t$1_s$2.tif costR_t$1_s$2.tif "
stereoSSD-mean -w $win_w -h $win_h -r $3 -R $4 left_image.tif right_image_t$1_s$2.tif disp_t$1_s$2.tif cost_t$1_s$2.tif dispR_t$1_s$2.tif costR_t$1_s$2.tif 


# 2. Filtering
echo "flat left_image.tif filt_flat_t$1_s$2.png $win_w"
flat left_image.tif filt_flat_t$1_s$2.png $win_w

echo "stereoLRRL disp_t$1_s$2.tif dispR_t$1_s$2.tif filt_LRRL_t$1_s$2.png 1"
stereoLRRL disp_t$1_s$2.tif dispR_t$1_s$2.tif filt_LRRL_t$1_s$2.png 1

echo "intersection filt_LRRL_t$1_s$2.png filt_flat_t$1_s$2.png filt_t$1_s$2.tif"
intersection filt_LRRL_t$1_s$2.png filt_flat_t$1_s$2.png filt_t$1_s$2.tif

echo "save_png_mask.sh filt_t$1_s$2.tif filt_t$1_s$2.png"
save_png_mask.sh filt_t$1_s$2.tif filt_t$1_s$2.png


# 3. Correct disparity values according to shear, tilt and translation parameters
echo "correction_disp_multi.sh $1 $2 0"
correction_disp_multi.sh $1 $2 0 


# 4. Generate png images for html display
echo "save_png.sh disp_t$1_s$2.tif disp_t$1_s$2.png $min_disparity $max_disparity"
save_png.sh disp_t$1_s$2.tif disp_t$1_s$2.png $min_disparity $max_disparity

echo "save_png.sh cost_t$1_s$2.tif cost_t$1_s$2.png 0 100"
save_png.sh cost_t$1_s$2.tif cost_t$1_s$2.png 0 100

