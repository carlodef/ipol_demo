#!/bin/bash
# usage:
# save_png.sh in out [minval] [maxval]

export PATH=$PATH:/usr/bin/:/usr/local/bin/

if [ $4 != "" ]; then
   plambda $1 "x[0] $3 fmax $4 fmin $3 - $4 $3 - / 255 *" 2> /dev/null | iion - $2 2> /dev/null 
# This line means:  (min(max(x,m),M) - m ) / (M-m) * 255
   addscale.py $2 $2 $3 $4
else
   plambda $1 "x[0]" 2> /dev/null | iion - $2 2> /dev/null
fi

