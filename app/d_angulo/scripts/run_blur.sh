#!/bin/bash

# $1: tilt parameter
# $2: gaussian std deviation

echo "blur left_image.png left_image_blurred_for_t$1.tif $2"
blur left_image.png left_image_blurred_for_t$1.tif $2
