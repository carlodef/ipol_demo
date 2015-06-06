#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/

# Parameters:
# $1: input filter (tif)
# $2: processed filter (png)

# Generate cyan transparent mask
convert -negate $1 -background cyan -alpha shape $2

