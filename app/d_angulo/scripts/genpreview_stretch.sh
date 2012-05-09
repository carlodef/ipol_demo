#!/bin/bash
# usage:
# genpreview_stretch.sh in out [minval] [maxval]

export PATH=$PATH:/usr/bin/:/usr/local/bin/

# check input
if [ "$4" != "" ]; then
#   (min(max(x,m),M) - m ) / (M-m) * 255
   plambda $1 "x[0] $3 fmax $4 fmin $3 - $4 $3 - / 255 *" | iion - $2 
   addscale.py $2 $2 $3 $4
else
   iion $1 $2
fi


