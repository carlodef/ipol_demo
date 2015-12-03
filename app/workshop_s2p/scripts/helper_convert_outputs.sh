#!/bin/bash

# horrible hack to add the folder bin/bin to the path
# in order to use qauto, iion and bin2asc
export PATH=/usr/local/bin:/usr/bin:/bin:$PATH
BINBIN=`dirname \`which s2p.py\``/bin
export PATH=$BINBIN:$PATH

bin2asc s2p_results/cloud.ply > cloud_ascii.ply

# produce previews for all the rectified images, diparity and height maps
if [ -d s2p_results/left ] ; then
    for f in s2p_results/{left,right}/tile_*
    do
        qauto $f/height_map.tif $f/height_map_preview.png &
        qauto $f/rectified_ref.tif $f/rectified_ref_preview.png &
        qauto $f/rectified_sec.tif $f/rectified_sec_preview.png &
        qauto $f/rectified_disp.tif $f/rectified_disp_preview.png &
        wait
    done
else
    for f in s2p_results/tile_*
    do
        qauto $f/height_map.tif $f/height_map_preview.png &
        qauto $f/rectified_ref.tif $f/rectified_ref_preview.png &
        qauto $f/rectified_sec.tif $f/rectified_sec_preview.png &
        qauto $f/rectified_disp.tif $f/rectified_disp_preview.png &
        wait
    done
fi

# get the path to the first tile (if it's a triplet, take the left dataset)
FIRST_TILE=`find s2p_results -type d -name "tile_*" | head -1`
echo "FIRST_TILE:" $FIRST_TILE

# symlinks to the results of the first tile
ln -fs $FIRST_TILE/rectified_ref_preview.png
ln -fs $FIRST_TILE/rectified_sec_preview.png
ln -fs $FIRST_TILE/rectified_disp_preview.png
