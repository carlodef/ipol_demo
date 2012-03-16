#!/bin/bash

export PATH=$PATH:/usr/bin/:/usr/local/bin/

# Load params
. params

addnoise input_0.png $sigma input_0_noised.png 
addnoise input_1.png $sigma input_1_noised.png

