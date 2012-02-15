#!/bin/bash

# $1 : tilt of the image (it is used to select the desired image among the list of all the tilted images)
# $2 : shear parameter

echo "shear input_1_t$1.png input_1_t$1_s$2.png $2 0"
shear input_1_t$1.png input_1_t$1_s$2.png $2 0
