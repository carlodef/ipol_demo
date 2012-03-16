#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/

# Load params
. params

# disparity for any pixel from col x is x*(-1 + 1/tilt)
# I add + 0*X[0] in the formula because I don't know how to get rid of x[0]
# but I need x as input to keep the dimensions of the image
plambda input_1.png "x[0] 0 * 1 $tilt / 1 - :i * +" > gt.tif 2> /dev/null
iion gt.tif gt.png
