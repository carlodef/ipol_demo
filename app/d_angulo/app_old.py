"""
Angulo
"""

from lib import base_app, build, http, image
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time
from utils import *


class app(base_app):
    """ Angulo """

    title = 'Angulo: Stereo block-matching with deformed patches'

    input_nb = 2 # number of input images
    input_max_pixels = 5000000 # max size (in pixels) of an input image
    input_max_weight = 1 * 10024 * 10024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    is_test = True       # switch to False for deployment
    is_listed = True


    def __init__(self):
        """
        App setup
        """
        # Setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # Select the base_app steps to expose
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
        Program build/update
        """
#        # Store common file path in variables
#        zip_url = 'http://www.ipol.im/pub/algo/' \
#        + 'ggm_random_phase_texture_synthesis/random_phase_noise_v1.3.zip'
#        zip_file = self.dl_dir + 'random_phase_noise_v1.3.zip'
#        prog = 'random_phase_noise'
#        bin_file = self.bin_dir + prog
#        sub_dir = os.path.join('random_phase_noise_v1.3', 'src')
#        log_file = self.base_dir + 'build.log'
#        # Get the latest source archive
#        build.download(zip_url, zip_file)
#        # Test if any dest file is missing, or too old
#        if (os.path.isfile(bin_file)
#            and ctime(zip_file) < ctime(bin_file)):
#            cherrypy.log('not rebuild needed',
#                         context='BUILD', traceback=False)
#        else:
#            # Extract the archive
#            build.extract(zip_file, self.src_dir)
#            # Build the programs
#            build.run("make -C %s %s"
#                      % (self.src_dir + sub_dir, prog),
#                      stdout=log_file)
#            # Save into bin dir
#            if os.path.isdir(self.bin_dir):
#                shutil.rmtree(self.bin_dir)
#            os.mkdir(self.bin_dir)
#            shutil.copy(self.src_dir + os.path.join(sub_dir, prog), bin_file)
#            # Cleanup the source dir
#            shutil.rmtree(self.src_dir)
        return

    @cherrypy.expose
    @init_app
#    Il faut forcement mettre une methode params car les methodes input_select
#    et input_upload, definies dans base_app.py et appelees par la page input.html,
#    renvoient a la methode params. Et celle qui est implementee dans base_app.py
#    renvoie la page params.html.
#    Le plus propre serait en fait de redefinir les methodes input_select et input_upload
#    dans app pour qu'elles renvoient a la methode crop directement.
    def params(self, msg=None, newrun=False):
        """
        Redirects to the crop page
        """
        if newrun:
            self.clone_input()
        
        return self.tmpl_out("crop.html", corners=0)
    
    
    @cherrypy.expose
    @init_app
    def crop(self, action=None, x=None, y=None, newrun=False):
        """
        select a rectangle in the image
        """
        if newrun:
            self.clone_input()
            return self.tmpl_out("params.html")

        elif action:
            # The crop is done, go to the parameters page
            return self.tmpl_out("params.html")
        
        else:
            # The user has not defined all the corners yet
            x = int(x)
            y = int(y)
            
            # Case 1 : nothing is defined
            if (not self.cfg['param'].has_key('x0')):
                
                self.cfg['param']['x0'] = x
                self.cfg['param']['y0'] = y
                
                # draw a cross at the first corner
                plot_cross(self.work_dir + 'input_0.png', x, y, \
                           self.work_dir + 'input_0_corner.png')
                
                # change the page
                return self.tmpl_out("crop.html", corners=1)
            
            # Case 2 : 1 corner is defined in the first image
            elif (not self.cfg['param'].has_key('x1')):

                self.cfg['param']['x1'] = x
                self.cfg['param']['y1'] = y
                
                # draw selection rectangle on the image
                x0 = self.cfg['param']['x0']
                y0 = self.cfg['param']['y0']
                plot_rectangle(self.work_dir + 'input_0.png', x0, y0, x, y, \
                               self.work_dir + 'input_0_selection.png')
                
                # crop from the first input image
                crop_image(self.work_dir + 'input_0.png', x0, y0, x, y, \
                           self.work_dir + 'input_0_cropped.png')
               
                return self.tmpl_out("crop.html", corners=2)
             
            # Case 3 : 2 corners defined in the first image    
            else:
                x0 = self.cfg['param']['x0']
                y0 = self.cfg['param']['y0']
                x1 = self.cfg['param']['x1']
                y1 = self.cfg['param']['y1']
                y2 = min(y0,y1)
                self.cfg['param']['x2'] = x
                self.cfg['param']['y2'] = y2
                x3 = x + abs(x1-x0)
                y3 = y2 + abs(y1-y0)    

                # draw selection rectangle on the image
                plot_rectangle(self.work_dir + 'input_1.png', x, y2, x3, y3, \
                               self.work_dir + 'input_1_selection.png')
                
                # crop from the first input image
                crop_image(self.work_dir + 'input_1.png', x, y2, x3, y3, \
                           self.work_dir + 'input_1_cropped.png')
                
                return self.tmpl_out("crop.html", corners=3)
            return


    @cherrypy.expose
    @init_app
    def wait_single_value(self, shear=None, tilt=None, win=None, 
                          disp_min=None, disp_max=None):
        """
        params handling and run redirection
        """
        try:
            shear = float(shear)
            tilt = float(tilt)
            win_w = int(win)
            win_h = int(win)
            disp_min = int(disp_min)
            disp_max = int(disp_max)
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        self.cfg['param']['type'] = 'single'
        self.cfg['param']['shear'] = shear
        self.cfg['param']['tilt'] = tilt
        self.cfg['param']['win_w'] = win_w
        self.cfg['param']['win_h'] = win_h
        self.cfg['param']['disp_min'] = disp_min
        self.cfg['param']['disp_max'] = disp_max
        self.cfg.save()

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")
    
    @cherrypy.expose
    @init_app
    def wait_multiple_values(self, shear_min=None, shear_max=None, shear_nb=None,
                             tilt_min=None, tilt_max=None, tilt_nb=None,
                             win=None, disp_min=None, disp_max=None):
        """
        params handling and run redirection
        """
        try:
            shear_min = float(shear_min)
            shear_max = float(shear_max)
            shear_nb = float(shear_nb)
            tilt_min = float(tilt_min)
            tilt_max = float(tilt_max)
            tilt_nb = float(tilt_nb)
            win_w = int(win)
            win_h = int(win)
            disp_min = int(disp_min)
            disp_max = int(disp_max)
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        self.cfg['param']['type'] = 'multiple'
        self.cfg['param']['shear_min'] = shear_min
        self.cfg['param']['shear_max'] = shear_max
        self.cfg['param']['shear_nb'] = shear_nb
        self.cfg['param']['tilt_min'] = tilt_min
        self.cfg['param']['tilt_max'] = tilt_max
        self.cfg['param']['tilt_nb'] = tilt_nb
        self.cfg['param']['win_w'] = win_w
        self.cfg['param']['win_h'] = win_h
        self.cfg['param']['disp_min'] = disp_min
        self.cfg['param']['disp_max'] = disp_max
        self.cfg.save()

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")


    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        
        # Generic parameters
        win_w = self.cfg['param']['win_w']
        win_h = self.cfg['param']['win_h']
        disp_min = self.cfg['param']['disp_min']
        disp_max = self.cfg['param']['disp_max']
        
        if (self.cfg['param']['type'] == 'single'):
            # read the other parameters
            shear = self.cfg['param']['shear']
            tilt = self.cfg['param']['tilt']
    
            # run the algorithm
            try:
                run_time = time.time()
                self.run_transform(shear, tilt)
#                self.run_transform()
                self.run_stereo(win_w, win_h, disp_min, disp_max, shear, tilt)
                self.cfg['info']['run_time'] = time.time() - run_time
                self.cfg.save()
            except TimeoutError:
                return self.error(errcode='timeout')
            except RuntimeError:
                return self.error(errcode='runtime')
            http.redir_303(self.base_url + 'result?key=%s' % self.key)

        
        elif (self.cfg['param']['type'] == 'multiple'):
            # read the other parameters
            shear_min = self.cfg['param']['shear_min']
            shear_max = self.cfg['param']['shear_max']
            shear_nb = self.cfg['param']['shear_nb']
            tilt_min = self.cfg['param']['tilt_min']
            tilt_max = self.cfg['param']['tilt_max']
            tilt_nb = self.cfg['param']['tilt_nb']
    
            # run the algorithm
            try:
                run_time = time.time()
                self.run_transform(shear, tilt)
                self.run_stereo(win_w, win_h, disp_min, disp_max, shear, tilt)
                self.cfg['info']['run_time'] = time.time() - run_time
                self.cfg.save()
            except TimeoutError:
                return self.error(errcode='timeout')
            except RuntimeError:
                return self.error(errcode='runtime')
            http.redir_303(self.base_url + 'result?key=%s' % self.key) 
        # archive
#        if self.cfg['meta']['original']:
#            ar = self.make_archive()
#            ar.add_file("input.png", info="input image")
#            ar.add_file("output.png", info="output image")
#            try:
#                fh = open(self.work_dir + 'input_selection.png')
#                fh.close()
#                ar.add_file("input_selection.png", info="input selection")
#                ar.add_file("input_0.orig.png", info="uploaded image")
#            except IOError:
#                pass
#            ar.add_info({"ratio": self.cfg['param']['ratio']})
#            ar.save()

        return self.tmpl_out("run.html")

    def run_transform(self, shear, tilt):
        """
        Applies an affine transform to the image input_1
        """
        # Computation of the new width
        width = image(self.work_dir + 'input_1_cropped.png').size[0]
        new_width = int(tilt*width)
        
        # Computes tilt on the right image
        p_tilt = self.run_proc(['zoom_1d', 'input_1_cropped.png', 'input_1_tilted.png',\
                                str(new_width)])
        self.wait_proc(p_tilt, timeout=self.timeout)

        # Compute shear on the tilted image
        p_shear = self.run_proc(['shear', 'input_1_tilted.png', 'input_1_transformed.png',\
                                str(shear), '0'])
        self.wait_proc(p_shear, timeout=self.timeout)

    def run_stereo(self, win_w, win_h, disp_min, disp_max, shear, tilt):
        """
        Computes the block_matching, on both the normal pair and the transformed pair
        """
                # Computation of the disparity range needed
        width = image(self.work_dir + 'input_0_cropped.png').size[0]
        if tilt < 1:
            disp_min_new = (tilt-1)*width+tilt*disp_min
            disp_max_new = tilt*disp_max
        else:
            disp_min_new = tilt*disp_min
            disp_max_new = (tilt-1)*width+tilt*disp_max
                
                # WRITE THE CONFIG FILE
        f = open(os.path.join(self.work_dir,'params'), 'w')
        f.write('win_w='+str(self.cfg['param']['win_w'])+'\n')
        f.write('win_h='+str(self.cfg['param']['win_h'])+'\n')
        f.write('disp_min='+str(self.cfg['param']['disp_min'])+'\n')
        f.write('disp_max='+str(self.cfg['param']['disp_max'])+'\n')
        f.write('disp_min_new='+str(disp_min_new)+'\n')
        f.write('disp_max_new='+str(disp_max_new)+'\n')
        f.write('shear='+str(self.cfg['param']['shear'])+'\n')
        f.write('tilt='+str(self.cfg['param']['tilt'])+'\n')
        f.close();
        
        # Run flat-patches first because it does not depend on disp maps
        p_flat = self.run_proc(['flat', 'input_0_cropped.png', 'filt_flat.png',\
                                 str(win_w)])
        self.wait_proc(p_flat, timeout=self.timeout)

        # Block-matching on the two pairs
        p_normal = self.run_proc(['/bin/bash', 'run_n.sh'])
        p_transformed = self.run_proc(['/bin/bash', 'run.sh'])
        self.wait_proc(p_normal, timeout=self.timeout)
        self.wait_proc(p_transformed, timeout=self.timeout)
            
#            # Filter with lrrl (tolerance 1) and flat patches
#        p_flat = self.run_proc(['flat', 'input_0_cropped.png', 'filt_flat.png',\
#                                 str(win_w)])
#        p_lrrl_n = self.run_proc(['stereoLRRL', 'disp_n.tif', 'dispR_n.tif',\
#                                'filt_LRRL_n.png', '1'])
#        p_lrrl = self.run_proc(['stereoLRRL', 'disp.tif', 'dispR.tif', 'filt_LRRL.png',\
#                                 '1'])
#        self.wait_proc(p_flat, timeout=self.timeout)
#        self.wait_proc(p_lrrl_n, timeout=self.timeout)
#        self.wait_proc(p_lrrl, timeout=self.timeout)
#            
#            # Intersect the filters
#        p_intersect_n = self.run_proc(['intersection', 'filt_LRRL_n.png',\
#                                      'filt_flat.png', 'filt_n.tif'])
#        p_intersect = self.run_proc(['intersection', 'filt_LRRL.png',\
#                                      'filt_flat.png', 'filt.tif'])
#        self.wait_proc(p_intersect_n, timeout=self.timeout)
#        self.wait_proc(p_intersect, timeout=self.timeout)
#            
#            # Generate transparent mask
#        p_transp_n = self.run_proc(['transp_mask.sh', 'filt_n.tif', 'filt_n.png'])
#        p_transp = self.run_proc(['transp_mask.sh', 'filt.tif', 'filt.png'])
#        self.wait_proc(p_transp_n, timeout=self.timeout)
#        self.wait_proc(p_transp, timeout=self.timeout)
#        
#            # Correction of disp values
#        p_correction = self.run_proc(['correction_disp.sh', str(tilt),\
#                                       str(shear), '0'])
#        self.wait_proc(p_correction, timeout=self.timeout)
#            
#            # Save disp and corr images as png files
#        p_png_n_1 = self.run_proc(['save_png.sh', 'disp_n.tif', 'disp_n.png',\
#                                str(disp_min), str(disp_max)])
#        p_png_n_2 = self.run_proc(['save_png.sh', 'corr_n.tif', 'corr_n.png', '0', '100'])
#        p_png_1 = self.run_proc(['save_png.sh', 'disp.tif', 'disp.png',\
#                                str(disp_min), str(disp_max)])
#        p_png_2 = self.run_proc(['save_png.sh', 'corr.tif', 'corr.png', '0', '100'])
#        self.wait_proc(p_png_n_1, timeout=self.timeout)
#        self.wait_proc(p_png_n_2, timeout=self.timeout)
#        self.wait_proc(p_png_1, timeout=self.timeout)
#        self.wait_proc(p_png_2, timeout=self.timeout)


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        sizeY=image(self.work_dir + 'input_0_cropped.png').size[1]
        return self.tmpl_out("result.html", sizeY=sizeY)
    
    
    
# We overwrite the clone_input method to copy also the cropped input images, in order
# to have a button 'change parameters' on the results page
    def clone_input(self):
        """
        clone the input for a re-run of the algo
        """
        self.log("cloning input from %s" % self.key)
        # get a new key
        old_work_dir = self.work_dir
        old_cfg_meta = self.cfg['meta']
        self.new_key()
        self.init_cfg()
        # copy the input files
        fnames = ['input_%i' % i + self.input_ext
                  for i in range(self.input_nb)]
        fnames += ['input_%i.png' % i
                   for i in range(self.input_nb)]
        fnames += ['input_%i_cropped.png' %i
                   for i in range(self.input_nb)]
        for fname in fnames:
            shutil.copy(old_work_dir + fname,
                        self.work_dir + fname)
        # copy cfg
        self.cfg['meta'].update(old_cfg_meta)
        self.cfg.save()
        return
