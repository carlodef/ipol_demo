import os
import re
import sys
import tempfile
import subprocess

# add the s2p_src/bin folder to system path
current_dir = os.path.dirname(os.path.abspath(__file__))
bin_dir = os.path.join(current_dir, 's2p_src', 'bin')
os.environ['PATH'] = bin_dir + os.pathsep + os.environ['PATH']

garbage = list()

def tmpfile(ext=''):
    """
    Creates a temporary file.

    Args:
        ext: desired file extension

    Returns:
        absolute path to the created file

    The path of the created file is added to the garbage list to allow cleaning
    at the end of the pipeline.
    """
    fd, out = tempfile.mkstemp(suffix=ext, prefix='s2p_', dir='.')
    garbage.append(out)
    os.close(fd)           # http://www.logilab.org/blogentry/17873
    return out

def run(cmd):
    """
    Runs a shell command, and print it before running.

    Arguments:
        cmd: string to be passed to a shell

    Both stdout and stderr of the shell in which the command is run are those
    of the parent process.
    """
    print cmd
    subprocess.call(cmd, shell=True, stdout=sys.stdout, stderr=subprocess.STDOUT,
        env=os.environ)
    return

def image_size_tiffinfo(im):
    """
    Reads the width and height of a tiff image, using tiffinfo.

    Args:
        im: path to the input tif image file
    Returns:
        a tuple of size 2, giving width and height
    """
    try:
        with open(im):
            p1 = subprocess.Popen(['tiffinfo', im], stdout=subprocess.PIPE, env=os.environ)
            p2 = subprocess.Popen(['grep', 'Image Width'], stdin=p1.stdout,
                    stdout=subprocess.PIPE, env=os.environ)
            line = p2.stdout.readline()
            out = re.findall(r"[\w']+", line)
            nc = int(out[2])
            nr = int(out[5])
            return (nc, nr)
    except IOError:
        print "image_size_tiffinfo: the input file %s doesn't exist" % str(im)


def image_size_identify(im):
    """
    Reads the width and height of any image, using identify (image magick).

    Args:
        im: path to the input image file
    Returns:
        a tuple of size 2, giving width and height
    """
    try:
        with open(im):
            # identify output example
            # /tmp/lena.png PNG 512x512 512x512+0+0 8-bit sRGB 475KB 0.000u 0:00.000
            p = subprocess.Popen(['identify', im], stdout=subprocess.PIPE, env=os.environ)
            nc, nr = p.stdout.readline().split()[2].split('x')
            return (nc, nr)
    except IOError:
        print "image_size_identify: the input file %s doesn't exist" % str(im)


def image_zoom_gdal(im, f, out=None, w=None, h=None):
    """
    Zooms an image using gdal (cubic interpolation)

    Args:
        im: path to the input image
        f:  zoom factor. f in [0,1] for zoom in, f in [1 +inf] for zoom out.
        out (optional): path to the ouput file
        w, h (optional): input image dimensions

    Returns:
        path to the output image. In case f=1, the input image is returned
    """
    if f == 1:
        return im

    if out is None:
        out = tmpfile('.tif')

    tmp = tmpfile('.tif')

    if w is None or h is None:
        sz = image_size_tiffinfo(im)
        w = sz[0]
        h = sz[1]

    # First, we need to make sure the dataset has a proper origin/spacing
    run('gdal_translate -a_ullr 0 0 %d %d %s %s' % (w/float(f), -h/float(f), im, tmp))

    # do the zoom with gdalwarp
    run('gdalwarp -r cubic -ts %d %d %s %s' %  (w/float(f), h/float(f), tmp, out))
    return out


def generate_preview(out, im):
    """
    Generates a small web-displayable preview image from a large tiff image

    Args:
        out: path to the output image file
        im: path to the input tif image file
    """
    w, h = image_size_tiffinfo(im)
    w = float(w)
    h = float(h)
    if os.path.splitext(out)[1].lower() != '.png':
        print "WARNING: generate_preview() can produce png files only"
    if w > 1366 or h > 768:
        if w/h > float(1366) / 768:
            f = w/1366
        else:
            f = h/768
        tmp = tmpfile('.tif')
        image_zoom_gdal(im, f, tmp, w, h)
        run('gdal_translate -of png -ot Byte -scale %s %s' % (tmp, out))
    else:
        run('gdal_translate -of png -ot Byte -scale %s %s' % (im, out))
    run('rm %s.aux.xml' % out)
    return out
