#!/usr/bin/env python
# This Python file uses the following encoding: utf-8

from __future__ import print_function
import subprocess
import shutil
import errno
import glob
import sys
import os
import re

import print_cfg

def mkdir_p(path):
    """
    Creates a directory without complaining if it already exists.
    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def symlink_p(src, dst):
    """
    Creates a symlink without complaining if it already exists.
    """
    try:
        os.symlink(src, dst)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.islink(dst):
            if os.path.realpath(dst) == os.path.realpath(src):
                pass
            else:
                print('%s is a link already pointing to %s' % (dst, os.path.realpath(dst)), file=sys.stderr)
        else:
            raise


def list_images_in_dataset(f):
    """
    Lists the TIF files of a dataset and finds corresponding P and MS.

    Args:
        f: absolute path to the dataset directory.

    Returns:
        a list. If the dataset contains only panchro images (P), then each item
        of the list is the absolute path to a panchro image. If the dataset
        contains both panchro (P) and multi-spectral images (MS), then each item
        of the list is a tuple containing the absolute paths to the P and MS tif
        images.
    """
    # list ms images
    # the '-not \( -path *_files -prune \)' is to avoid entering in the dzi
    # folders, which contains tens of thousands jpeg files and make the process
    # very slow
    p = subprocess.Popen("find %s -not \( -path *_files -prune \) -type f -name \"*_MS_*.JP2.TIF\"" % f, shell=True, stdout=subprocess.PIPE)
    ms_files = p.stdout.read().splitlines()
    p = subprocess.Popen("find %s -not \( -path *_files -prune \) -type f -name \"*_P_*.JP2.TIF\"" % f, shell=True, stdout=subprocess.PIPE)
    pan_files = p.stdout.read().splitlines()
    if not ms_files:
        print("no MS images in dataset %s" % f, file=sys.stderr)
        return pan_files
    else:
        out = []
        for ms in ms_files:
            try:
                date_ms = re.split('_', os.path.basename(ms))[3]
            except IndexError:
                print("non standard filename in dataset %s" % f, file=sys.stderr)
                return pan_files
            # search for the pan file with the same date
            matching_pan = None
            for pan in pan_files:
                if re.split('_', os.path.basename(pan))[3] == date_ms:
                    matching_pan = pan
                    break
            if matching_pan is None:
                print("no matching panchro image found for %s" % ms, file=sys.stderr)
            else:
                out.append((matching_pan, ms))
        return out


def copy_file_matching_pathname(pattern, src, dest):
    """
    Args:
        pattern: may contain simple shell-style wildcards
        src: directory where to search for filenames matching the pattern
        dest: directory where to copy the matching files and create links

    Returns:
        absolute path of the copied file if a single file was found and copied,
        None otherwise.
    """
    l = glob.glob(os.path.join(src, pattern))
    if not l:
        print('No filename matching %s in directory %s' % (pattern, src), file=sys.stderr)
    elif len(l) > 1:
        print('More than one file %s in directory %s: ' % (pattern, src), l, file=sys.stderr)
    else:
        shutil.copy(l[0], dest)
        return os.path.abspath(os.path.join(dest, os.path.basename(l[0])))


def create_links(list_of_paths, dest_dir, print_cfg_ipol=False):
    """
    Creates symlinks to the pleiades image files and metadata files of a dataset.

    Args:
        list_of_paths: list of paths to panchro TIF files, produced by the
            list_images_in_dataset function. All the files belong to the same dataset.
        dest_dir: directory where to create the symlinks for the dataset.
        print_cfg: set to True to print cfg file for IPOL demos on stdout.
    """
    ms = False
    for i, f in enumerate(list_of_paths):

        if isinstance(f, tuple):  # we have the ms image
            # tif ms
            ms = True
            symlink_p(f[1], os.path.join(dest_dir, 'im_ms_%02d.tif' % (i+1)))

            # preview ms
            tmp = copy_file_matching_pathname('PREVIEW_*.JPG', os.path.dirname(f[1]), dest_dir)
            if tmp:
                symlink_p(tmp, os.path.join(dest_dir, 'prv_%02d.jpg' % (i+1)))
                # enhance contrast
                # os.system("/home/carlo/code/s2p/bin/qauto %s %s" % (tmp, tmp)
            else:
                print('MS PREVIEW not found for %s' % f[1], file=sys.stderr)
            f = f[0]  # the path to ms preview is not needed anymore

        # pan preview (if no ms preview)
        if not os.path.isfile(os.path.join(dest_dir, 'prv_%02d.jpg' % (i+1))):
            tmp = copy_file_matching_pathname('PREVIEW_*.JPG', os.path.dirname(f), dest_dir)
            if tmp:
                symlink_p(tmp, os.path.join(dest_dir, 'prv_%02d.jpg' % (i+1)))
                # os.system("/home/carlo/code/s2p/bin/qauto %s %s" % (tmp, tmp))
            else:
                print('PAN PREVIEW not found for %s' % f, file=sys.stderr)

        # dim
        tmp = copy_file_matching_pathname('DIM_*.XML', os.path.dirname(f), dest_dir)
        if tmp:
            symlink_p(tmp, os.path.join(dest_dir, 'dim_%02d.xml' % (i+1)))

        # rpc
        tmp = copy_file_matching_pathname('RPC_*.XML', os.path.dirname(f), dest_dir)
        if tmp:
            symlink_p(tmp, os.path.join(dest_dir, 'rpc_%02d.xml' % (i+1)))

        # tif panchro
        symlink_p(f, os.path.join(dest_dir, 'im_panchro_%02d.tif' % (i+1)))

        # dzi 8 bits
        dzi8_found = False
        dzi8 = '%s_8BITS.dzi' % f[:-8]  # remove extension '.JP2.TIF' (8 chars)
        files8 = '%s_8BITS_files' % f[:-8]
        if os.path.isfile(dzi8) and os.path.isdir(files8):
            symlink_p(dzi8, os.path.join(dest_dir, 'im_panchro_8BITS_%02d.dzi' % (i+1)))
            symlink_p(files8, os.path.join(dest_dir, 'im_panchro_8BITS_%02d_files' % (i+1)))
            dzi8_found = True

        # dzi 16 bits
        dzi16_found = False
        dzi16 = '%s_16BITS.dzi' % f[:-8]  # remove extension '.JP2.TIF' (8 chars)
        files16 = '%s_16BITS_files' % f[:-8]
        if os.path.isfile(dzi16) and os.path.isdir(files16):
            symlink_p(dzi16, os.path.join(dest_dir, 'im_panchro_16BITS_%02d.dzi' % (i+1)))
            symlink_p(files16, os.path.join(dest_dir, 'im_panchro_16BITS_%02d_files' % (i+1)))
            dzi16_found = True

        # print warning if neither 8bit nor 16bit dzi was found
        if (not dzi8_found) and (not dzi16_found):
            print('WARNING: no dzi file found for img %s' % f, file=sys.stderr)

    if print_cfg_ipol:
        print_cfg.main(dest_dir, len(list_of_paths), ms)


def main(src_dir, dst_dir='pleiades', print_cfg_ipol=False):
    """
    Creates links to the pleiades images contained in the source directory.

    Args:
        src_dir: path to the folder containing the pleiades data
        dst_dir: path to the folder where to create the links
        print_cfg: set to True to print cfg file for IPOL demos on stdout.
    """
    for dataset in os.listdir(src_dir):
        dataset_abspath = os.path.join(src_dir, dataset)
        if os.path.isdir(dataset_abspath):
            if 'dataset_1' in os.listdir(dataset_abspath):  # the dataset has subdatasets (multidate)
                for subdataset in os.listdir(dataset_abspath):
                    if os.path.isdir(os.path.join(dataset_abspath, subdataset)):
                        l = list_images_in_dataset(os.path.join(dataset_abspath, subdataset))
                        mkdir_p(os.path.join(dst_dir, dataset, subdataset))
                        create_links(l, os.path.join(dst_dir, dataset, subdataset), print_cfg_ipol)
            else:  # the dataset doesn't have subdatasets (monodate)
                l = list_images_in_dataset(dataset_abspath)
                mkdir_p(os.path.join(dst_dir, dataset))
                create_links(l, os.path.join(dst_dir, dataset), print_cfg_ipol)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('\tusage: %s src_dir [dst_dir (default pleiades)] > index.cfg' % sys.argv[0], file=sys.stderr)
    elif len(sys.argv) == 2:
        main(sys.argv[1], print_cfg_ipol=True)
    else:
        main(sys.argv[1], sys.argv[2], print_cfg_ipol=True)
