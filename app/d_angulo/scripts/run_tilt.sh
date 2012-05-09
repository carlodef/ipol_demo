#!/bin/bash

# $1: tilt parameter
# $2: output width

echo "zoom_1d right_image.tif right_image_t$1.tif $2"
zoom_1d right_image.tif right_image_t$1.tif $2

