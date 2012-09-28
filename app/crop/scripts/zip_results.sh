#!/bin/bash

export PATH=$PATH:/bin:/usr/bin
if [ -f out_gt.tif ]
then
    zip tif_zipped out_0.tif out_1.tif out_gt.tif out_gt_mask.tif
else
    zip tif_zipped out_0.tif out_1.tif
fi


