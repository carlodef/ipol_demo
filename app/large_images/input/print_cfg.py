#!/usr/bin/env python
# This Python file uses the following encoding: utf-8

from __future__ import print_function
import subprocess
import sys
import os
import re


def extract_date_from_pleiades_filename(filename):
    """
    """
    date = re.split('_', os.path.basename(filename))[3]
    # we assume that the date has the following format: 201210051030181
    return '%s-%s-%s' % (date[:4], date[4:6], date[6:8])


def extract_satellite_from_pleiades_filename(filename):
    """
    """
    satellite = re.split('_', os.path.basename(filename))[1]
    if satellite == 'PHR1A':
        return '1A'
    elif satellite == 'PHR1B':
        return '1B'
    else:
        return '1X'


def grep_xml(xml_file, tag):
    """
    Reads the value of an element in an xml file.

    Args:
        xml_file: path to the xml file
        tag: start/end tag delimiting the desired element

    Returns:
        A string containing the element written between <tag> and </tag>
        Only the value of the element associated to the first occurence of the
        tag will be returned.
    """
    try:
        with open(xml_file):
            p1 = subprocess.Popen(['grep', tag, xml_file],
                    stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['cut', '-d', '>', '-f', '2'],
                    stdin=p1.stdout, stdout=subprocess.PIPE)
            p3 = subprocess.Popen(['cut', '-d', '<', '-f', '1'],
                    stdin=p2.stdout, stdout=subprocess.PIPE)
            lines = p3.stdout.read().splitlines()
            if not lines:
                print("grep_xml: no tag %s in file %s" % (tag, xml_file))
                return
            if len(lines) > 1:
                print("grep_xml: WARNING several occurences of %s in file %s" % (tag, xml_file))
            return lines[0]
    except IOError:
        print("grep_xml: the input file %s doesn't exist" % xml_file)
        sys.exit()


def main(dataset, out):
    """
    """
    # read list of paths to img files
    f = open(os.path.join(dataset, 'paths_panchro.txt'))
    path_list = f.readlines()
    f.close()
    n = len(path_list)

    # build lists of paths to dzi and previews files
    prv_paths = ' '.join([os.path.join('pleiades', dataset, 'prev_panchro_%02d.jpg' % (i+1)) for i in xrange(n)])
    tif_paths = ' '.join([os.path.join('pleiades', dataset, 'im_panchro_%02d.tif' % (i+1)) for i in xrange(n)])
    dzi8_paths, dzi16_paths = None, None
    if os.path.isfile(os.path.abspath(os.path.join(dataset,
                                                   'im_panchro_8BITS_01.dzi'))):
        dzi8_paths  = ' '.join([os.path.join('input', 'pleiades', dataset,
                                             'im_panchro_8BITS_%02d.dzi' %
                                             (i+1)) for i in xrange(n)])
    if os.path.isfile(os.path.abspath(os.path.join(dataset,
                                                   'im_panchro_16BITS_01.dzi'))):
        dzi16_paths = ' '.join([os.path.join('input', 'pleiades', dataset,
                                             'im_panchro_16BITS_%02d.dzi' %
                                             (i+1)) for i in xrange(n)])

    # read infos in DIM*.XML file
    dim_xml_file = os.path.join(dataset, 'dim_panchro_01.xml')
    if os.path.isfile(dim_xml_file):  # check if the link points to an existing file
        date = grep_xml(dim_xml_file, "IMAGING_DATE")
        satellite = grep_xml(dim_xml_file, "INSTRUMENT_INDEX")
    else:
        date = extract_date_from_pleiades_filename(os.readlink(os.path.join(dataset, 'im_panchro_01.tif')))
        satellite = extract_satellite_from_pleiades_filename(os.readlink(os.path.join(dataset, 'im_panchro_01.tif')))

    # print to input.cfg
    if dzi8_paths or dzi16_paths:
        print('[pleiades/%s]' % dataset, file=out)
        print('prv = ', prv_paths, file=out)
        print('tif = ', tif_paths, file=out)
        if dzi8_paths:
            print('dzi8 = ', dzi8_paths, file=out)
        if dzi16_paths:
            print('dzi16 = ', dzi16_paths, file=out)
        s = os.path.split(dataset)
        if s[0]:  # ie the path is of the kind 'reunion/dataset_1'
            print('title = %s (%s)' % (s[0].capitalize(), s[1][-1]), file=out)  # ie 'Reunion (1)'
        else:  # ie the path is of the kind 'reunion'
            print('title = %s' % s[1].capitalize(), file=out)  # ie 'Reunion'
        print('date = %s' % date, file=out)
        print('satellite = Pleiades %s' % satellite, file=out)
        print('nb_img = %d' % n, file=out)
        print('color = panchro', file=out)

if __name__ == '__main__':
    out = open('../index.cfg', 'a')
    main(sys.argv[1], out)
    out.close()
