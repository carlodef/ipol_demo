#!/bin/bash

#load params
. params

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin

#Remove extra canals from cost maps
ls cost_t*.tif > cost_maps
for i in `cat cost_maps`; do 
	echo $i
	plambda $i "x[0]" 2> /dev/null | iion - $i 2> /dev/null
	
done

# Do the merge
echo "merge filt_t*.tif cost_t*.tif disp_t*.tif out_disp out_argmin out_cost.tif"
merge filt_t*.tif cost_t*.tif disp_t*.tif out_disp.tif out_argmin.tif out_cost.tif

# Save the output disp as a png file
echo "save_png.sh out_disp.tif out_disp.png $min_disparity $max_disparity"
save_png.sh out_disp.tif out_disp.png $min_disparity $max_disparity

# Intersect all the filters to get the filter corresponding to out_disp.tif
echo "union filt_t*.tif out_filt.tif"
union filt_t*.tif out_filt.tif

echo "transp_mask.sh out_filt.tif out_filt.png"
save_png_mask.sh out_filt.tif out_filt.png


# Convert the out_argmin image into a HSV image with tilt=hue and shear=value
echo "visualize out_argmin.tif $tilt_min $tilt_max $shear_min $shear_max out_argmin.png"
visualize out_argmin.tif $tilt_min $tilt_max $shear_min $shear_max out_argmin.png

# Convert the out_cost image into a png file
echo "save_png.sh out_cost.tif out_cost.png 0 100"
save_png.sh out_cost.tif out_cost.png 0 100
