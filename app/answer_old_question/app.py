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
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt


class app(base_app):
    """ Tilt quantization tests"""

    title = "A tentative answer to an old question"
    input_nb = 1 # number of input images
    input_max_pixels = 2048 * 2048 # max size (in pixels) of an input image
    input_max_weight = 10 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = True       # switch to False for deployment
    
    def build(self):
        """
        program build/update
        """
        # useful file paths
        log_file = self.base_dir + "build.log"
        self.src_dir = self.src_dir + "stereo";
        
        # Import the code from git repository
        import os
        os.system("git clone --depth 1 ssh://fuchsia/home/facciolo/code/stereo.git "+self.src_dir)
        # TODO: use git archive (see below) instead of git clone to download only the source code (and not the doc)
        #os.system("git archive --remote=ssh://fuchsia/home/facciolo/code/stereo.git -o src.tar -v master src")
                
        # Create bin dir (delete the previous one if exists)
        if os.path.isdir(self.bin_dir):
            shutil.rmtree(self.bin_dir)
        os.mkdir(self.bin_dir)
        
        # build the program
        build.run("make -C %s %s" % (self.src_dir, "all"), stdout=log_file)

        # cleanup the source dir
        shutil.rmtree(self.src_dir)
        
        # link all the scripts to the bin dir
        import glob
        for file in glob.glob( os.path.join( self.base_dir, 'scripts/*')):
            os.symlink(file, os.path.join( self.bin_dir , os.path.basename(file)))
    
        return

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

    def print_debug(self,string):
        print ""
        print ""
        print "***********************"+string+"***********************"

          
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
        self.print_debug("First tilt")
        new_width = int(tilt*width)
        p_first_tilt = self.run_proc(['zoom_1d', 'input_0.png', 'input_1.png', str(new_width)])
        self.wait_proc(p_first_tilt, timeout=self.timeout)
        
        # Generate ground truth for the matching of input_1 (as left image) with input_0 (as right image)
        self.print_debug("Generate GT")
        p_gt = self.run_proc(['/bin/bash', 'run_generate_gt.sh', 'input_1.png'])
        self.wait_proc(p_gt, timeout=self.timeout)
        
        # list of tilts
        self.print_debug("List of tilts")
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
        print tilt_list
        
        
        # disp range for the input pair :
        self.print_debug("List of disp ranges")
        if tilt < 1:
                    disp_min = -5
                    disp_max = width-new_width
        else:
                    disp_min = width-new_width
                    disp_max = 5
        
        # List of disparity range needed
        disp_bounds = {}
        for t in tilt_list:
            if t < 1:
                    d_m = (t-1)*new_width+t*disp_min
                    d_M = t*disp_max
            else:
                    d_m = t*disp_min
                    d_M = (t-1)*new_width+t*disp_max
            disp_bounds[t] = (d_m, d_M)
        print disp_bounds
        
        # Compute all the tilted right images
        self.print_debug("Compute all the tilts")
        p = {}
        for t in tilt_list:
            t_str = '%1.2f' % t
            p[t] = self.run_proc(['/bin/bash', 'run_tilt.sh', t_str, str(int(t*width))])
        for t in tilt_list:
            self.wait_proc(p[t], timeout=self.timeout)
        
        # Do the block-matching, filtering and compute statistics on all the simulated pairs
        self.print_debug("Compute the block-matchings")
        for t in tilt_list:
            t_str = '%1.2f' % t
            (d_m,d_M) = disp_bounds[t]
            p[t] = self.run_proc(['/bin/bash', 'run_bm.sh', t_str, str(d_m), str(d_M)])
        for t in tilt_list:
            self.wait_proc(p[t], timeout=self.timeout)
    
        
        # Plot the graph of RMSE
        self.print_debug("Plot the rmse graph")
        rmse = []
        i=0
        for t in tilt_list:
            t_str = '%1.2f' % t
            disperror = open(self.work_dir+"/"+"stat_t"+t_str+".txt","r").read().split()
            rmse.append(disperror[2])
        print rmse
        
        fig = plt.figure()
        plt.grid(True)
        plt.plot(tilt_list, rmse, 'bo')
        fig.savefig(self.work_dir+"rmse.png")
        
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        sizeY=image(self.work_dir + 'input_1.png').size[1]

        return self.tmpl_out("result.html", sizeY=sizeY)
