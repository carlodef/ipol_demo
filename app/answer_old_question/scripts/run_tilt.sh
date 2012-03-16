#!/bin/bash

# $1: tilt parameter
# $2: output width

echo "zoom_1d input_0.png input_0_t$1.png $2"
zoom_1d input_0_noised.png input_0_t$1.png $2

