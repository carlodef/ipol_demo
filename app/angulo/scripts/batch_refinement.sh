#!/bin/bash

# This shell script is called after batch_angulo.py. It does the following
# * zip the needed files
# * copy them on remote server at cmla
# * call script that calls matlab on remote server

# input arguments:
# $1: key

export PATH=$PATH:/bin:/usr/bin

# compress the files
tar cv left_image.tif right_image.tif out_disp.tif out_tilt.tif out_shear.tif out_filt.tif | gzip -9 - > $1.tar.gz

# copy the archive on caviar 
scp $1.tar.gz caviar:~/code/ipol_demo/app/d_angulo/tmp/

# run the processing script on sel 
ssh sel "/bin/bash ~/code/batch_script.sh $1"

