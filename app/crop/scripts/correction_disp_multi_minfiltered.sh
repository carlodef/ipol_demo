#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/

#Correction of the disparity maps with plambda
#Usage : 
#	correction_disp_multi_minfiltered zoom shear translation
# $1: zoom 
# $2: shear
# $3: translation

# Load params
. params

# if the shear is negative, the correction is different because in the shear executable there is an extra translation of shear*height performed in that case
# This hack works only for shears that are strictly more than -1 and less than 1
sign_shear=`echo $2 | cut -d'.' -f 1`
echo $sign_shear
if [ $sign_shear == "-0" ] || [ $sign_shear == "-1" ]; then
echo "Correction of NEGATIVE SHEAR" 
plambda m_disp_t$1_s$2.tif "x[0] :j $2 * - $3 - $2 $height * +" > m_disp_t$1_s$2_corrected1 2> /dev/null
else
echo "Correction of POSITIVE SHEAR"
plambda m_disp_t$1_s$2.tif "x[0] :j $2 * - $3 -" > m_disp_t$1_s$2_corrected1 2> /dev/null
fi
plambda m_disp_t$1_s$2_corrected1 "1 $1 / 1 - :i * x $1 / +" > m_disp_t$1_s$2.tif 2> /dev/null

