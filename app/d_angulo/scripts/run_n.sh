#!/bin/bash

#load params
. params

# Subpixel environment variable
export SUBPIXEL=$subpixel
echo $SUBPIXEL

echo "stereoSSD-mean -w $win_w -h $win_h -r $disp_min -R $disp_max input_0_cropped.png input_1_cropped.png disp_n.tif corr_n.tif dispR_n.tif corrR_n.tif &"
stereoSSD-mean -w $win_w -h $win_h -r $disp_min -R $disp_max input_0.png input_1.png disp_n.tif corr_n.tif dispR_n.tif corrR_n.tif &

wait

echo "stereoLRRL disp_n.tif dispR_n.tif filt_LRRL_n.png 1"
stereoLRRL disp_n.tif dispR_n.tif filt_LRRL_n.png 1

echo "intersection filt_LRRL_n.png filt_flat.png filt_n.tif"
intersection filt_LRRL_n.png filt_flat.png filt_n.tif

echo "transp_mask.sh filt_n.tif filt_n.png &"
transp_mask.sh filt_n.tif filt_n.png &

echo "save_png.sh disp_n.tif disp_n.png $disp_min $disp_max &"
save_png.sh disp_n.tif disp_n.png $disp_min $disp_max &

echo "save_png.sh corr_n.tif corr_n.png 0 100"
save_png.sh corr_n.tif corr_n.png 0 100

# Catch bg processes
wait
