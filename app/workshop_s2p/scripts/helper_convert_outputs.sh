#!/bin/bash

# horrible hack to add the folder bin/bin to the path
# in order to use qauto, iion and bin2asc
export PATH=/usr/bin:/usr/local/bin:/bin:$PATH
BINBIN=`dirname \`which s2p.py\``/bin
export PATH=$BINBIN:$PATH

qauto s2p_results/roi_ref.tif s2p_results/roi_ref_preview.png
qauto s2p_results/roi_sec.tif s2p_results/roi_sec_preview.png
qauto s2p_results/dem.tif s2p_results/dem_preview.png
bin2asc s2p_results/cloud.ply > cloud_ascii.ply

# some datasets don't have color images
if [ -f s2p_results/roi_color_ref.tif ]; then
    qauto s2p_results/roi_color_ref.tif s2p_results/roi_color_ref_preview.png
fi

# some datasets have only pairs (no left right subfolders)
if [ -d s2p_results/left ] ; then
    for f in s2p_results/{left,right}/tile_*
    do
        qauto $f/dem.tif $f/dem_preview.png &
        qauto $f/rectified_ref.tif $f/rectified_ref_preview.png &
        qauto $f/rectified_sec.tif $f/rectified_sec_preview.png &
        qauto $f/rectified_disp.tif $f/rectified_disp_preview.png &
        wait
    done
else
    for f in s2p_results/tile_*
    do
        qauto $f/dem.tif $f/dem_preview.png &
        qauto $f/rectified_ref.tif $f/rectified_ref_preview.png &
        qauto $f/rectified_sec.tif $f/rectified_sec_preview.png &
        qauto $f/rectified_disp.tif $f/rectified_disp_preview.png &
        wait
    done
fi
