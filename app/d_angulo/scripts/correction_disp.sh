#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/

#Correction of the disparity maps with plambda
#Usage : 
#	correction_disp zoom shear translation
# $1: zoom 
# $2: shear
# $3: translation

plambda disp.tif "x[0] :j $2 * - $3 -" > disp_corrected1
plambda disp_corrected1 "1 $1 / 1 - :i * x $1 / +" > disp.tif
