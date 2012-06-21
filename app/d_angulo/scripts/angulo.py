#!/usr/bin/python
#

import os
import sys

def run(cmd):
    """
    Print the provided command, then ask the shell to run it, and 
    print all the messages that would appear in the shell. It seems to
    wait that the command terminates.
    """
    print cmd
    fin, fout = os.popen4(cmd)
    print fout.read()


def load_parameters():
    """
    Reads the file index.cfg in the working directory (tmp/key/) and convert
    it in a dictionary. Copied from Nicolas Limare's method 'load' in file lib/config.py
    """
    import ConfigParser
    infile = file('index.cfg')
    infile.seek(0)
    try:
        cfg = ConfigParser.RawConfigParser()
        cfg.readfp(infile)
    except Exception:
        raise ValueError('File not in recognized format')
    # convert the config file into a dict
    cfgdict = dict()
    for section in cfg.sections():
        cfgdict[section] = dict()
        for option in cfg.options(section):
            # read from most to least restrictive methods
            value = None
            for reader in (cfg.getboolean, cfg.getfloat, cfg.getint):
                try:
                    value = reader(section, option)
                except ValueError:
                    pass
            # string in last resort
            if value == None:
                value = cfg.get(section, option)
            cfgdict[section][option] = value 
    infile.close()
    return cfgdict


def compute_list(m, M, nb):
    """
    Outputs a list of values arithmetically sampled between m and M,
    such that there are nb values in the output list
    """
    out = [m]
    if nb > 1 :
        delta = abs(M - m) / (nb - 1)
        i = 1
        while (i < nb):
            value = m + i * delta
            out.append(value)
            i += 1
    return out


def compute_bounds(tilts, shears, im_width, min_disparity, max_disparity):
    """
    Outputs a dictionary containing the disparity range needed for
    each pair (tilt,shear)
    """            
    # TODO : correct the formula to take shear into account
    out = {}
    for t in tilts:
        for s in shears:
            if t < 1:
                m = (t - 1) * im_width + t * min_disparity
                M = t * max_disparity
            else:
                m = t * min_disparity
                M = (t - 1) * im_width + t * max_disparity
            out[t, s] = (m, M)
    return out


def write_config_file_for_shell(config_dict):
    """
    Writes the config file used by the shell scripts
    """
    f = open('params','w')
    f.write('win_w=' + str(config_dict['param']['windowsize']) + '\n')
    f.write('win_h=' + str(config_dict['param']['windowsize']) + '\n')
    f.write('min_disparity=' + str(config_dict['param']['min_disparity']) + '\n')
    f.write('max_disparity=' + str(config_dict['param']['max_disparity']) + '\n')
    f.write('tilt_min=' + str(config_dict['param']['tilt_min']) + '\n')
    f.write('tilt_max=' + str(config_dict['param']['tilt_max']) + '\n')
    f.write('shear_min=' + str(config_dict['param']['shear_min']) + '\n')
    f.write('shear_max=' + str(config_dict['param']['shear_max']) + '\n')
    f.write('subpixel=' + str(config_dict['param']['subpixel']) + '\n')
    f.write('height=' + str(config_dict['param']['image_height']) + '\n')
    f.close();


def apply_tilts(tilts, im_width):
    """
    Compute all the deformed (tilted) right images
    """
    for t in tilts:
        t_str = '%1.2f' % t
        out_w = str(int(t * im_width))
        run('/bin/bash run_tilt.sh %s %s' % (t_str, out_w))


def apply_shears(tilts, shears):
    """
    Compute all the deformed (tilt+shear) right images
    """
    for t in tilts:
        t_str = '%1.2f' % t
        for s in shears:
            s_str = '%1.2f' % s
            run('/bin/bash run_shear.sh %s %s' % (t_str, s_str))


def block_matching_and_filtering(tilts, shears, disp_bounds):
    """
    Run the block-matching and filtering on all the simulated pairs
    """
    for t in tilts:
        t_str = '%1.2f' % t
        for s in shears:
            s_str = '%1.2f' % s
            (m, M) = disp_bounds[t, s]
            run('/bin/bash run_multi.sh %s %s %d %d' % (t_str, s_str, m, M))
       

def merge_maps():
    """
    Merge the disparity maps
    """
    run('/bin/bash run_merge.sh')
        

def rendering():
    """        
    Generate 3D rendering
    """
    run('/bin/bash run_render.sh')
        

def cleanup():
    """
    Cleanup the tmp dir
    """
    run('/bin/bash run_clean.sh')


def main():
    """
    Angulo algorithm
    """
    # load input parameters
    config_dict = load_parameters()    
    shear_min = config_dict['param']['shear_min']
    shear_max = config_dict['param']['shear_max']
    shear_nb = config_dict['param']['shear_nb']
    tilt_min = config_dict['param']['tilt_min']
    tilt_max = config_dict['param']['tilt_max']
    tilt_nb = config_dict['param']['tilt_nb']
    min_disparity = config_dict['param']['min_disparity']
    max_disparity = config_dict['param']['max_disparity']
    im_width = config_dict['param']['image_width']

    # compute other parameters
    tilt_list = compute_list(tilt_min, tilt_max, tilt_nb)
    shear_list = compute_list(shear_min, shear_max, shear_nb)        
    disparity_bounds = compute_bounds(tilt_list, shear_list, im_width, min_disparity, max_disparity)
    
    # do the job
    write_config_file_for_shell(config_dict)
    apply_tilts(tilt_list, im_width)
    apply_shears(tilt_list, shear_list)
    block_matching_and_filtering(tilt_list, shear_list, disparity_bounds)
    merge_maps()
    rendering()
    cleanup()

# main call
if __name__ == '__main__': main()

