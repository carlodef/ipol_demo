#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/

#Correction of the disparity maps with plambda
#Usage : 
#	correction_disp zoom
# $1: zoom 

# Load params
. params

plambda disp_t$1.tif "1 $1 / 1 - :i * x[0] $1 / +" > disp_t$1_corrected.tif 2> /dev/null

