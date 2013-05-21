"""
rgbprocess ipol demo web app
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.misc import gzip
from lib.misc import prod
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time

class app(base_app):
    """ rgbprocess app """

    title = "Image Color Cube Dimensional Filtering and Visualization"
    xlink_article = 'http://www.ipol.im/pub/art/2011/blm-cdf/'

    input_nb = 1
    input_max_pixels = 500 * 500 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = False

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_url = "http://www.ipol.im/pub/art/2011/blm-cdf/rgbprocess.tar.gz"
        tgz_file = self.dl_dir + "rgbprocess.tar.gz"
        prog_file = self.bin_dir + "rgbprocess"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download(tgz_url, tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s rgbprocess"
                      % (self.src_dir + "rgbprocess"),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir 
                        + os.path.join("rgbprocess", "rgbprocess"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return


    #
    # PARAMETER HANDLING
    #

    @cherrypy.expose
    @init_app
    def rectangle(self, action=None, x=None, y=None, x0=None, y0=None):
        """
        select a rectangle in the image
        """
        if action == 'run':
            # use the whole image
            img = image(self.work_dir + 'input_0.png')
            img.save(self.work_dir + 'input' + self.input_ext)
            img.save(self.work_dir + 'input.png')
            # go to the wait page, with the key
            http.redir_303(self.base_url + "wait?key=%s" % self.key)
            return
        else:
            # use a part of the image
            if x0 == None:
                # first corner selection
                x = int(x)
                y = int(y)
                # draw a cross at the first corner
                img = image(self.work_dir + 'input_0.png')
                img.draw_cross((x, y), size=4, color="white")
                img.draw_cross((x, y), size=2, color="red")
                img.save(self.work_dir + 'input.png')
                return self.tmpl_out("params.html", x0=x, y0=y)
            else:
                # second corner selection
                x0 = int(x0)
                y0 = int(y0)
                x1 = int(x)
                y1 = int(y)
                # reorder the corners
                (x0, x1) = (min(x0, x1), max(x0, x1))
                (y0, y1) = (min(y0, y1), max(y0, y1))
                assert (x1 - x0) > 0
                assert (y1 - y0) > 0
                # draw selected rectangle on the image
                imgS = image(self.work_dir + 'input_0.png')
                imgS.draw_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], color="red")
                imgS.draw_line([(x0+1, y0+1), (x1-1, y0+1), (x1-1, y1-1), (x0+1, y1-1), (x0+1, y0+1)], color="white")
                imgS.save(self.work_dir + 'input_0s.png')
                # crop the image
		# try cropping from the original input image (if different from input_0)
		im0 = image(self.work_dir + 'input_0.orig.png')
		(dx0, dy0) = im0.size
                img = image(self.work_dir + 'input_0.png')
                (dx, dy) = img.size
		if (dx != dx0) :
                    z=float(dx0)/float(dx)
                    im0.crop((int(x0*z), int(y0*z), int(x1*z), int(y1*z)))
                    # resize if cropped image is too big
                    if self.input_max_pixels and prod(im0.size) > (self.input_max_pixels):
                        im0.resize(self.input_max_pixels, method="antialias")
                    img=im0
                    # im0.save(self.work_dir + 'input.png')
                    # img = image(self.work_dir + 'input.png')
		else :
                    img.crop((x0, y0, x1, y1))
                # zoom the cropped area
                (dx, dy) = img.size
                if (dx < 400) and (dy < 400) :
                    if dx > dy :
                        dy = int(float(dy) / float(dx) * 400)
                        dx = 400
                    else :
                        dx = int(float(dx) / float(dy) * 400)
                        dy = 400
                    img.resize((dx, dy), method="bilinear")
                img.save(self.work_dir + 'input' + self.input_ext)
                img.save(self.work_dir + 'input.png')
                # go to the wait page, with the key
                http.redir_303(self.base_url + "wait?key=%s" % self.key)
            return

    @cherrypy.expose
    @init_app
    def wait(self):
        """
        params handling and run redirection
        """
        # no parameters
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algorithm execution
        """
        stdout = open(self.work_dir + 'stdout.txt', 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')

	stdout.close();

        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", info="uploaded image")
            ar.add_file("input_0.png", info="full-size")
	    if (os.path.isfile(self.work_dir + 'input_0s.png') == True) :
		ar.add_file("input_0s.png", info="sub-image selection")
            ar.add_file("input.png", info="input image")
            ar.add_file("output_2.png", info="output image")
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, stdout=None, timeout=30):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
		
	#print number of pixels of the input image to stdout
        img = image(self.work_dir + 'input.png')
        (dx, dy) = img.size
	stdout.write("Number of pixels of input image: %i" %(dx*dy))
	stdout.flush()

        p1 = self.run_proc(['rgbprocess', 'rmisolated',
                            'input.png', 'input_1.png'],
                           stdout=stdout, stderr=stdout)
        p2 = self.run_proc(['rgbprocess', 'RGBviewsparams',
                            'RGBviewsparams.txt'],
                           stdout=None, stderr=stdout)
        self.wait_proc([p1, p2], timeout)

        p3 = self.run_proc(['rgbprocess', 'filter',
                            'input_1.png', 'output_1.png'],
                           stdout=None, stderr=stdout)
        wOut = 300
        hOut = 300
        displayDensity = 0
        p4 = self.run_proc(['rgbprocess', 'RGBviews',
                            'input_1.png', 'RGBviewsparams.txt', 'inRGB', 
                            str(wOut), str(hOut), str(displayDensity)],
                           stdout=None, stderr=stdout)
        self.wait_proc([p3, p4], timeout)

        p5 = self.run_proc(['rgbprocess', 'RGBviews',
                            'output_1.png', 'RGBviewsparams.txt', 'outRGB', 
                            str(wOut), str(hOut), str(displayDensity)],
                           stdout=None, stderr=stdout)
        displayDensity = 1
        p6a = self.run_proc(['rgbprocess', 'densityimage',
                            'output_1.png', 'dstyimage.png'],
                           stdout=None, stderr=stdout)
        self.wait_proc([p5, p6a], timeout)
        p6b = self.run_proc(['rgbprocess', 'RGBviews',
                            'output_1.png', 'RGBviewsparams.txt', 'dstyRGB', 
                           str(wOut), str(hOut), str(displayDensity), 'dstyimage.png'],
                           stdout=None, stderr=stdout)
        self.wait_proc(p6b, timeout)

        p7 = self.run_proc(['rgbprocess', 'combineviews',
                            'RGBviewsparams.txt',
                            'inRGB', 'outRGB', 'dstyRGB', 'view'], 
                           stdout=None, stderr=stdout)
        p8 = self.run_proc(['rgbprocess', 'mergeimages',
                            'output_1.png', 'input.png', 'output_2.png'],
                           stdout=None, stderr=stdout)
        self.wait_proc([p7, p8], timeout)

        p9 = self.run_proc(['rgbprocess', 'countcolors',
                            'output_2.png'],
                           stdout=stdout, stderr=stdout)
        p10 = self.run_proc(['rgbprocess', 'computeRMSE',
                            'input.png', 'output_2.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc([p9, p10], timeout)

	
        displayDensity = 0
        p11 = self.run_proc(['rgbprocess', 'RGB2VRML2',
                            'input_1.png', 'input_1_RGB.wrl', str(displayDensity)],
                           stdout=None, stderr=None)
	p12 = self.run_proc(['rgbprocess', 'RGB2VRML2',
                            'output_1.png', 'output_1_RGB.wrl', str(displayDensity)],
                           stdout=None, stderr=None)
        displayDensity = 1
        p13 = self.run_proc(['rgbprocess', 'RGB2VRML2',
                            'output_1.png', 'output_1_RGBd.wrl', str(displayDensity), 'dstyimage.png'],
                           stdout=None, stderr=None)
        self.wait_proc([p11, p12, p13], timeout)

	#compress .wrl files
        for fname in ["input_1_RGB", "output_1_RGB", "output_1_RGBd"]:
          gzip(self.work_dir + fname + ".wrl")


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
			     useOriginal=os.path.isfile(self.work_dir + 'input_0s.png'),
                             sizeY="%i" % image(self.work_dir + 'input.png').size[1])
