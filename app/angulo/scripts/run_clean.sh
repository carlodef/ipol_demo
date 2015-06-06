#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin

# Cleanup tif files
echo "rm disp*.tif cost*.tif filt*.tif"
rm disp*.tif cost*.tif filt*.tif

# Cleanup "corrected" images
echo "rm *_corrected*"
rm *_corrected*
