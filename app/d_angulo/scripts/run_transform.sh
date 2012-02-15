#!/bin/bash

#load params
. params

echo "zoom_1d input_1.png input_1_tilted.png $1"
zoom_1d input_1.png input_1_tilted.png $1

echo "shear input_1_tilted.png input_1_transformed.png $shear 0"
shear input_1_tilted.png input_1_transformed.png $shear 0
