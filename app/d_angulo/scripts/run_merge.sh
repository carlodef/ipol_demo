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

# Do the merge for the minfiltered maps (option 2)
#merge filt_t*.tif m_cost_t*.tif m_disp_t*.tif out_disp_minfiltered2.tif out_argmin_minfiltered2.tif out_cost_minfiltered2.tif
#save_png.sh out_disp_minfiltered2.tif out_disp_minfiltered2.png $disp_min $disp_max
#visualize out_argmin_minfiltered2.tif $tilt_min $tilt_max $shear_min $shear_max out_argmin_minfiltered2.png


 
# Apply the minfilter (in its special version adapted for angulo, ie option 1)
#echo "Angulo special minfilter"
#minfilter_angulo 7 out_disp.tif out_cost.tif out_argmin.tif out_disp_minfiltered.tif out_cost_minfiltered.tif out_argmin_minfiltered.tif
#save_png.sh out_disp_minfiltered.tif out_disp_minfiltered.png $disp_min $disp_max
#visualize out_argmin_minfiltered.tif $tilt_min $tilt_max $shear_min $shear_max out_argmin_minfiltered.png


# Save the output disp as a png file
echo "save_png.sh out_disp.tif out_disp.png $disp_min $disp_max"
save_png.sh out_disp.tif out_disp.png $disp_min $disp_max

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
#save_png.sh out_cost_minfiltered.tif out_cost_minfiltered.png 0 100
#save_png.sh out_cost_minfiltered2.tif out_cost_minfiltered2.png 0 100
