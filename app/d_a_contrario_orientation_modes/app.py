"""
demo A contrario detection of modes in orientation histogram
"""

from lib import base_app, build, http, image, config
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time

class app(base_app):
    """ detection of modes app"""

    title = "A contrario detection of modes in orientation histogram"
    input_nb = 1 # number of input images
    input_max_pixels = 512 * 512 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = True       # switch to False for deployment

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
        tgz_urls = ['https://edit.ipol.im/edit/algo/d_a_contrario_orientation_modes/' \
            + tgz_name for tgz_name in ['modes_detection.tar.gz', 'addnoise.tar.gz']]
        tgz_files = [self.dl_dir
            + tgz_name for tgz_name in ['modes_detection.tar.gz', 'addnoise.tar.gz']]
        progs = ['modes_detection', 'addnoise']
        log_file = self.base_dir + 'build.log'

        # get the latest source archives
        for tgz_url, tgz_file in zip(tgz_urls, tgz_files):
            build.download(tgz_url, tgz_file)

        # first prog : modes_detection
        # test if the dest file is missing, or too old
        if (os.path.isfile(self.bin_dir + progs[0])
                 and ctime(tgz_files[0]) < ctime(self.bin_dir + p)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_files[0], self.src_dir)

            # build the program
            build.run("make -C %s" % (self.src_dir + progs[0]),
                      stdout=log_file)

            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + progs[0] + '/' + progs[0], self.bin_dir + progs[0])

            # cleanup the source dir
            shutil.rmtree(self.src_dir)

        # second prog : addnoise
        # test if the dest file is missing, or too old
        if (os.path.isfile(self.bin_dir + progs[1])
                 and ctime(tgz_files[1]) < ctime(self.bin_dir + p)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_files[1], self.src_dir)

            # build the program
            build.run("make -C %s" % (self.src_dir + progs[1]),
                      stdout=log_file)

            # save into bin dir
            shutil.copy(self.src_dir + progs[1] + '/' + progs[1], self.bin_dir + progs[1])

            # cleanup the source dir
            shutil.rmtree(self.src_dir)

        return
    
    @cherrypy.expose
    def get_params_from_url(self, input_id=None, x=None, y=None, r=None, n_bins= None, sigma=None):
        """
        redirects to the wait method with the provided parameters
        This method was made only to be able to launch one precise experiment from one url
        """
        self.new_key()
        self.init_cfg()
        
        # get the images
        input_dict = config.file_dict(self.input_dir)
        fnames = input_dict[input_id]['files'].split()
        for i in range(len(fnames)):
            shutil.copy(self.input_dir + fnames[i],
                        self.work_dir + 'input_%i' % i)
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg['meta']['input_id'] = input_id
        self.cfg.save()
        
        # jump to the wait page
        return self.wait(key=self.key, newrun=False, xold="0", yold="0",
                          x=x, y=y, r=r, sigma=sigma, n_bins=n_bins)

    @cherrypy.expose
    @init_app
    def wait(self, newrun=False, xold="0", yold="0", x="-1", y="-1", r="15", sigma="0", n_bins="36"):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()

        if float(x)<0:
            x=xold
            y=yold

        # save and validate the parameters
        try:
	    x = float(x)
	    y = float(y)
            r = float(r)
            sigma = float(sigma)
            n_bins = int(n_bins)
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        self.cfg['param'] = {'x' : x, 'y' : y, 'r' : r, 'sigma' : sigma, 'n_bins' : n_bins}
        self.cfg.save()

        """
        run redirection
        """
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")


    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        # read the parameters
        x = self.cfg['param']['x']
        y = self.cfg['param']['y']
        r = self.cfg['param']['r']
        sigma = self.cfg['param']['sigma']
        n_bins = self.cfg['param']['n_bins']

        # run the algorithm
        try:
	    run_time = time.time()
            self.run_algo(x,y,r,sigma,n_bins)
	    self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("input_0.orig.png", "original.png", info="uploaded image")
            ar.add_file("input_0.png", "input.png", info="input image")
	    ar.add_file("histo_ac.png", info="a contrario detected modes")
 	    ar.add_file("histo_lowe.png", info="lowe's maxima")
            ar.add_file("output_ac.png", info="a contrario orientations")
	    ar.add_file("output_lowe.png", info="lowe's orientations")
            ar.add_info({"x": x, "y": y, "r": r, "n_bins": n_bins, "sigma":sigma})
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self, x, y, r, sigma, n_bins):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
	# Add noise
        p_0 = self.run_proc(['addnoise', 'input_0.png', str(sigma), 'input_1.png'])
        self.wait_proc(p_0, timeout=self.timeout)

	# Detect modes with both methods (AC and Lowe)
        p_1 = self.run_proc(['modes_detection', 'input_1.png', str(x),  str(y),  str(r),\
        str(n_bins), '0'])
        self.wait_proc(p_1, timeout=self.timeout)

	# Draw circle and arrows on the input_1 images, for AC and then for Lowe
        from plot_orientations import *
        plot_orientations(self.work_dir + 'input_1.png', x, y, r,\
        self.work_dir + 'modes_ac.txt', self.work_dir + 'output_ac.png')

        from plot_orientations import *
        plot_orientations(self.work_dir + 'input_1.png', x, y, r,\
        self.work_dir + 'modes_lowe.txt', self.work_dir + 'output_lowe.png')

	# Plot modes, AC and then Lowe
        from plot_modes import *
        plot_modes(self.work_dir + 'histo_ac.txt', self.work_dir + 'modes_ac.txt',\
        self.work_dir + 'histo_ac.png', n_bins)

        from plot_modes import *
        plot_modes(self.work_dir + 'histo_lowe.txt', self.work_dir + 'modes_lowe.txt',\
        self.work_dir + 'histo_lowe.png', n_bins)

        return


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        sizeX=image(self.work_dir + 'input_0.png').size[0]
        sizeY=image(self.work_dir + 'input_0.png').size[1]

        return self.tmpl_out("result.html", sizeX=sizeX, sizeY=sizeY)
