"""
Recovering the Subpixel PSF from Two Photographs at Different Distances
"""

from lib import base_app, build, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time

class app(base_app):
    """ demo app """
    
    title = "Recovering the Subpixel PSF from Two Photographs"\
            " at Different Distances" 
           
    xlink_article = 'http://www.ipol.im/pub/art/2013/77/'
    input_nb = 2 # number of input images
    input_max_pixels = 5000000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '1x8i' # input image expected data type
    input_ext = '.pgm'   # input image expected extension (ie file format)
    is_test = False      # switch to False for deployment

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() is generic
        app_expose(base_app.index)
        app_expose(base_app.input_select)
        app_expose(base_app.input_upload)
        # params() is modified from the template
        app_expose(base_app.params)
        # run() and result() must be defined here

    def build(self):
        """
        program build/update
        """
        # store common file path in variables
        tgz_file = self.dl_dir + "two-photos-psf-estim.tar.gz"
        prog_file = self.bin_dir + "two_photos_psf_estim"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download("http://www.ipol.im/pub/art/2013/77/"
                       + "two-photos-psf-estim.tar.gz", tgz_file)

        # test if the dest file is missing, or too old
        # dont rebuild the file
        if  (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)) :
            cherrypy.log("not rebuild needed",
            context='BUILD', traceback=False)
        else:
            #extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make OMP=1 -j4 -C %s two_photos_psf_estim" 
                      % (self.src_dir + "two-photos-psf-estim"), stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + os.path.join("two-photos-psf-estim", 
                        "two_photos_psf_estim"), prog_file) 
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    @cherrypy.expose
    @init_app
    def wait(self, s="3", k="13", t="0"):
        """
        params handling and run redirection
        """
        # save and validate the parameters
        try:
            self.cfg['param'] = {'s' : int(s),
                                 'k' : int(k),
                                 't' : int(t)}
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        s = self.cfg['param']['s']
        k = self.cfg['param']['k']
        t = self.cfg['param']['t']
        # save standard outputx
        stdout = open(self.work_dir + 'stdout.txt', 'w')

        # run the algorithm
        try:
            run_time = time.time()
            self.run_algo(s, k, t, stdout=stdout)
            self.cfg['info']['run_time'] = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            stdout_text = open(self.work_dir + 'stdout.txt', 'r').read() 
            
            if stdout_text.find("Images do not match.")!=-1:
                http.redir_303(self.base_url + 
                               'result?key=%s&error_nomatch=1' % self.key)    
       
            return self.error('returncode', 'Unknown Run Time Error')

        http.redir_303(self.base_url + 'result?key=%s' % self.key)
       

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.png", info="uploaded #1")
            ar.add_file("input_1.png", info="uploaded #2")
            ar.add_file("psf_kernel.txt", info="psf_kernel.txt", compress=True)
            ar.add_file("psf_kernel.png", info="psf_kernel.png")
            ar.add_file("int_kernel.txt", compress=True)
            ar.add_file("int_kernel.png")
            ar.add_file("stdout.txt", compress=True)
            ar.add_info({"s": s, "k": k, "t":t})
            ar.add_info({"run time" : self.cfg['info']['run_time']})
            ar.save()
        return self.tmpl_out("run.html")

    def run_algo(self, s, k, t, stdout=None):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
        p = self.run_proc(['two_photos_psf_estim',
                           '-s', str(s),
                           '-k', str(k),
			   '-t', str(t),
                           '-d', 'ipol',
                           '-o', 'psf_kernel.pgm',
			   '-i', 'int_kernel.pgm',
                           'input_0.pgm', 
                           'input_1.pgm', 
                           'psf_kernel.txt', 
                           'int_kernel.txt'],
                            stdout=stdout, stderr=stdout)
        self.wait_proc(p)               
                
        im = image(self.work_dir + "psf_kernel.pgm")
        # re adjust width and height to avoid visualization interpolation
        width = 600
        height = 600
        # interpolate it by neareset neighbor
        im = im.resize((width, height), "nearest") 
        im.save(self.work_dir + "psf_kernel.png")
		
        im = image(self.work_dir + "int_kernel.pgm")
        # re adjust width and height to avoid visualization interpolation
        width = 600
        height = 600
        # interpolate it by neareset neighbor
        im = im.resize((width, height), "nearest") 
        im.save(self.work_dir + "int_kernel.png")
        # convert images from .pgm to .png
        im = image(self.work_dir + "ipol_imgC.pgm")
        im.save(self.work_dir + "ipol_imgC.png")

        im = image(self.work_dir + "ipol_imgW.pgm")
        im.save(self.work_dir + "ipol_imgW.png")

        im = image(self.work_dir + "ipol_diff.pgm")
        im.save(self.work_dir + "ipol_diff.png")	

        im = image(self.work_dir + "ipol_mask.pgm")
        im.save(self.work_dir + "ipol_mask.png")
						
        return

    @cherrypy.expose
    @init_app
    def result(self, error_nomatch=None):
        """
        display the algo results
        """
        height = max(image(self.work_dir + 'input_0.png').size[1],
                     image(self.work_dir + 'input_1.png').size[1])
        if error_nomatch:
            return self.tmpl_out("result_nomatch.html", height=height)
        else:
            return self.tmpl_out("result.html", height=height)
