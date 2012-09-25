#/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin:.

#load params
. params

# Subpixel parameter
export SUBPIXEL=$subpixel

# Provided arguments:
# $1 : tilt parameter 
# $2 : shear parameter
# $3 : disp_min current
# $4 : disp_max current
# $5 : tilt flag, 1 if t>1 and 0 if not 


# 0.  tilt > 1. This determines if the left image is blurred or not
left=left_image.tif
if [ $5 -eq 1 ]; then
    echo "dilating tilt, apply blur to left image"
    left=left_image_blurred_for_t$1.tif
fi
    

# 1. Do the block-matching: this is the time-consuming step
stereoSSD-mean -w $win_w -h $win_h -r $3 -R $4 $left right_image_t$1_s$2.tif disp_t$1_s$2.tif cost_t$1_s$2.tif dispR_t$1_s$2.tif costR_t$1_s$2.tif 

# 2. Filtering
flatH $left filt_flat_t$1_s$2.png $win_w
stereoLRRL2 disp_t$1_s$2.tif dispR_t$1_s$2.tif filt_LRRL_t$1_s$2.png 1
intersection filt_LRRL_t$1_s$2.png filt_flat_t$1_s$2.png filt_t$1_s$2.tif
save_png_mask.sh filt_t$1_s$2.tif filt_t$1_s$2.png

# 3. Correct disparity values according to shear, tilt and translation parameters
correction_disp.sh $1 $2 0 

# 4. Generate png images for html display
save_png.sh disp_t$1_s$2.tif disp_t$1_s$2.png $min_disparity $max_disparity
save_png.sh cost_t$1_s$2.tif cost_t$1_s$2.png 0 100

