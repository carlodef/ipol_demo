"""
demo Shear and tilt
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
    """ shear and Tilt"""

    title = "Shear and tilt illustration"
    input_nb = 1 # number of input images
    input_max_pixels = 512 * 512 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = True       # switch to False for deployment
    is_listed = False
    xlink_article = 'www.ipol.im'

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

    
    @cherrypy.expose
    @init_app
    def wait(self, tilt=None, shear=None):
        """
        configure the algo execution
        """
        # save and validate the parameters
        try:
	    tilt = float(tilt)
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        self.cfg['param']['tilt'] = tilt
        self.cfg['param']['shear'] = shear
        self.cfg['param']['width'] = image(self.work_dir+'input_0.png').size[0]
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
        tilt = self.cfg['param']['tilt']
        shear = self.cfg['param']['shear']

        # run the algorithm
        try:
	    run_time = time.time()
            self.run_algo(tilt, shear)
	    self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        return self.tmpl_out("run.html")

    def run_algo(self, tilt, shear):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        
    # Write the config file
        f = open(os.path.join(self.work_dir,'params'), 'w')
        f.write('shear='+str(self.cfg['param']['shear'])+'\n')
        f.close();
        
	# Computes tilt and shear on the right image
        width = self.cfg['param']['width']
        new_width = int(tilt*width)
        p_transform = self.run_proc(['/bin/bash', 'run_transform.sh', str(new_width)])
        self.wait_proc(p_transform, timeout=self.timeout)
    
    
#    # Tilt
#        width = self.cfg['param']['width']
#        new_width = int(tilt*width)
#        p_0 = self.run_proc(['zoom_1d', 'input_0.png', 'input_1.png', str(new_width)])
#        self.wait_proc(p_0, timeout=self.timeout)
#        
#    # Shear
#        width = self.cfg['param']['width']
#        new_width = int(tilt*width)
#        p_0 = self.run_proc(['zoom_1d', 'input_0.png', 'input_1.png', str(new_width)])
#        self.wait_proc(p_0, timeout=self.timeout)


        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        sizeY=image(self.work_dir + 'input_0.png').size[1]

        return self.tmpl_out("result.html", sizeY=sizeY)
