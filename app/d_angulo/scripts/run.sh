#!/bin/bash

#load params
. params

# Subpixel environment variable
export SUBPIXEL=$subpixel
echo $SUBPIXEL

echo "stereoSSD-mean -w $win_w -h $win_h -r $disp_min_new -R $disp_max_new input_0.png input_1_transformed.png disp.tif corr.tif dispR.tif corrR.tif &"
stereoSSD-mean -w $win_w -h $win_h -r $disp_min_new -R $disp_max_new input_0.png input_1_transformed.png disp.tif corr.tif dispR.tif corrR.tif &

wait

echo "stereoLRRL disp.tif dispR.tif filt_LRRL.png 1"
stereoLRRL disp.tif dispR.tif filt_LRRL.png 1

echo "correction_disp.sh $tilt $shear 0 &"
correction_disp.sh $tilt $shear 0 &

echo "intersection filt_LRRL.png filt_flat.png filt.tif"
intersection filt_LRRL.png filt_flat.png filt.tif

echo "transp_mask.sh filt.tif filt.png"
transp_mask.sh filt.tif filt.png

wait

echo "save_png.sh disp.tif disp.png $disp_min $disp_max &"
save_png.sh disp.tif disp.png $disp_min $disp_max &

echo "save_png.sh corr.tif corr.png 0 100"
save_png.sh corr.tif corr.png 0 100

# Catch background processes
wait
