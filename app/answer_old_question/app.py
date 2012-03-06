"""
demo to determine how to quantize tilts for angulo 
"""

from lib import base_app, build, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time
from collections import deque

class app(base_app):
    """ Tilt quantization tests"""

    title = "A tentative answer to an old question"
    input_nb = 1 # number of input images
    input_max_pixels = 2048 * 2048 # max size (in pixels) of an input image
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

    
    @cherrypy.expose
    @init_app
    def wait(self, tilt=None, tilts_half_nb=None):
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
        self.cfg['param']['tilts_half_nb'] = tilts_half_nb
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

        # run the algorithm
        try:
	    run_time = time.time()
            self.run_algo()
	    self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        return self.tmpl_out("run.html")

    def run_algo(self):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        # Read parameters
        width = self.cfg['param']['width']
        tilt = self.cfg['param']['tilt']
        tilts_half_nb = self.cfg['param']['tilts_half_nb']
        
        # Write the config file
        f = open(os.path.join(self.work_dir,'params'), 'w')
        f.write('width='+str(width)+'\n')
        f.write('tilt='+str(tilt)+'\n')
        f.write('tilts_half_nb='+str(tilts_half_nb)+'\n')
        f.write('win_w='+str(9)+'\n')
        f.write('win_h='+str(9)+'\n')
        f.close();
        
        # Computes tilt on the image
        new_width = int(tilt*width)
        p_first_tilt = self.run_proc(['zoom_1d', 'input_0.png', 'input_1.png', str(new_width)])
        self.wait_proc(p_first_tilt, timeout=self.timeout)
        
        # Generate ground truth for the matching of input_1 (as left image) with input_0 (as right image)
        p_gt = self.run_proc(['/bin/bash', 'run_generate_gt.sh', 'input_1.png'])
        self.wait_proc(p_gt, timeout=self.timeout)
        
        # list of tilts
        k = pow(2,1./tilts_half_nb)
        tilt_list = deque([tilt])
        i = 1
        while (i<=tilts_half_nb):
            factor = pow(k,i)
            t = tilt * factor
            tilt_list.append(t)
            t = tilt / factor
            tilt_list.appendleft(t)
            i += 1
        self.cfg['param']['tilt_list'] = tilt_list
        self.cfg.save()
        
        # List of disparity range needed
        disp_bounds = {}
        for t in tilt_list:
            if t < tilt:
                d_m = (t-tilt)*width
                d_M = 0
            else:
                d_m = 0
                d_M = (t-tilt)*width
            disp_bounds[t] = (d_m, d_M)
        
        # Compute all the tilted right images
        p = {}
        for t in tilt_list:
            t_str = '%1.2f' % t
            p[t] = self.run_proc(['/bin/bash', 'run_tilt.sh', t_str, str(int(t*width))])
        for t in tilt_list:
            self.wait_proc(p[t], timeout=self.timeout)
        
        # Do the block-matching and filtering on all the simulated pairs
        for t in tilt_list:
            t_str = '%1.2f' % t
            (d_m,d_M) = disp_bounds[t]
            p[t] = self.run_proc(['/bin/bash', 'run_multi.sh', t_str, str(d_m), str(d_M)])
        for t in tilt_list:
            self.wait_proc(p[t], timeout=self.timeout)
    
    
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
#        p_transform = self.run_proc(['/bin/bash', 'run_transform.sh', str(new_width)])


        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        sizeY=image(self.work_dir + 'input_1.png').size[1]

        return self.tmpl_out("result.html", sizeY=sizeY)
