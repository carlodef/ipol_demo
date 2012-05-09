#!/bin/bash

# $1 : tilt of the image (it is used to select the desired image among the list of all the tilted images)
# $2 : shear parameter

echo "shear right_image_t$1.tif right_image_t$1_s$2.tif $2 0"
shear right_image_t$1.tif right_image_t$1_s$2.tif $2 0
