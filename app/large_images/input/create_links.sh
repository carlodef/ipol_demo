#!/bin/bash

function create_links ()
# $1: directory where to create the links, and containing the txt file $2
# $2: txt file containing the list of paths to images
# $3: suffix for link names. "_panchro" for panchro, "_ms" for multispectral, "_pxs" for pansharpened
{
    dataset=$1
    files_list=$2
    suffix=$3
    i=0
    for image in `cat $dataset/$files_list`
        do
            i=$(($i+1))
            # dzi image
            link_name=`printf im$suffix\_%02d.dzi $i`
            ln -sf $image $dataset/$link_name
            # dzi files
            link_name=`printf im$suffix\_%02d_files $i`
            ln -sf ${image%.*}_files $dataset/$link_name
            # preview - the wildcard '*' does the job if we assume there is
            # ONLY ONE image per folder
            abs_path=`dirname $image`/PREVIEW_*.JPG
            link_name=`printf prev$suffix\_%02d.jpg $i`
            cp $abs_path $dataset/
            ln -sf `basename $abs_path` $dataset/$link_name
    done
}


###############
# Main script #
###############

# arguments:
# $1: absolute path to the folder containing the pleiades data

# check input (ie the pleiades data folder)
if [ ! $1 ] ; then
    printf "\tusage: %s pleiades_data_folder_path\n" $0
    exit
fi

pleiades_dir=$1
if [ ! -d $pleiades_dir ] ; then
    printf "\tincorrect path to pleiades data folder\n"
    exit
fi

# step 1: parse the pleiades data folder to extract the paths to *.dzi images
for f in $pleiades_dir/*; do
    if [ -d $f ]; then
        mkdir -p `basename $f`
        if ls $f/dataset_* &> /dev/null; then
            # the dataset has subdatasets (multidate)
            for ff in $f/dataset_*; do
                mkdir -p `basename $f`/`basename $ff`
                find $ff -not \( -path *_files -prune \) -type f -name "*_P_*16BITS.dzi" | sort > `basename $f`/`basename $ff`/paths_panchro.txt
                find $ff -not \( -path *_files -prune \) -type f -name "*_MS_*16BITS.dzi" | sort > `basename $f`/`basename $ff`/paths_ms.txt
                find $ff -not \( -path *_files -prune \) -type f -name "*_PXS_*16BITS.dzi" | sort > `basename $f`/`basename $ff`/paths_pxs.txt
            done
        else
            # the dataset has no subdatasets
            find $f -not \( -path *_files -prune \) -type f -name "*_P_*16BITS.dzi" | sort > `basename $f`/paths_panchro.txt
            find $f -not \( -path *_files -prune \) -type f -name "*_MS_*16BITS.dzi" | sort > `basename $f`/paths_ms.txt
            find $f -not \( -path *_files -prune \) -type f -name "*_PXS_*16BITS.dzi" | sort > `basename $f`/paths_pxs.txt
        fi
    fi
done

# step 2: create the symlinks
for dataset in `find * -type d`; do
    if [ -s "$dataset/paths_panchro.txt" ] ; then
        create_links $dataset "paths_panchro.txt" "_panchro"
    fi
    if [ -s "$dataset/paths_ms.txt" ] ; then
        create_links $dataset "paths_ms.txt" "_ms"
    fi
    if [ -s "$dataset/paths_pxs.txt" ] ; then
        create_links $dataset "paths_pxs.txt" "_pxs"
    fi
done
