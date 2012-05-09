"""
Angulo web app
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
    timeout = 90
    is_test = True       # switch to False for deployment
    is_listed = False

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
        App setup
        """
        # Setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # Select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True # A changer ?
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True



############ INPUT HANDLING ################################################################
########## COPIED FROM GABRIELE ############################################################


    # ONLY THESE INPUTS ARE ACCEPTED
    VALID_KEYS=[ 'left_image_url', 'right_image_url', 
                 'ground_truth_url', 'ground_truth_mask_url', 
                 'left_image', 'right_image', 
                 'ground_truth', 'ground_truth_mask', 'ground_truth_occ',
                 'scale_gt_b', 'scale_gt_a', 
                 'min_disparity', 'max_disparity',
                 # THESE ARE EXECUTION PARAMETERS
                 'decision_method', 'block_match_method', 'filter_method', 
                 'windowsize', 'noise_sigma', 'action',
                 'run', 'input_data_url', 'input_data', 'subpixel' , 'preprocess'
                 ]

    # these are files 
    FILE_KEYS=[ 'left_image', 'right_image', 'ground_truth', 'ground_truth_mask', 'ground_truth_occ', 'input_data']

    # Default parameters
    default_param = dict(
          {  'windowsize': 9,
             'min_disparity': -31,
             'max_disparity': 31,
             'noise_sigma': 0,
             'addednoisesigma': 0,
             'image_width': 800,
             'image_height': 600,
             'scale_gt_a' : 1,
             'scale_gt_b' : 0,
             'subpixel' : 1
             }.items()
          )
    
    def copy_cfg_from_path(self, cfgfile, destdir):
        """
        Read the configuration from a local file, 
        the files are assumed to be in the same subdirectory as the cfg file.
        The configuration file can contain both references to local files, 
        and references to remote URL's.
        The local files are copied to the /dl directory,
        the processing of urls is postponed
        """
        import urlparse
        import os

        # SOURCE DIR
        srcdir = os.path.dirname(cfgfile)

        # create download directory if does not exist
        dl_dir = os.path.join(destdir,'dl')
        if not os.path.exists(dl_dir):
           os.mkdir(dl_dir)

        # DEFAULT PARAM
        self.cfg['param'] = self.default_param.copy()

        # LOAD param.cfg
        # TODO : must be done with eval , MAYBE SOME OTHER SOLUTION?
        f = file(cfgfile); 
        params = eval(f.read()); 
        f.close()
        shutil.copy(cfgfile, dl_dir)

        # Load self.cfg with non-null params
        for key in self.VALID_KEYS:
           if key in params.keys():
              self.cfg['param'][key] = params[key];
           else:
              if key not in self.cfg['param'].keys():
                 self.cfg['param'][key]='' 

        # COPY the files
        for key in self.FILE_KEYS:
            if key in params.keys():
               if params[key] != '':
                  oname = params[key]
                  dname = key + os.path.splitext(oname)[1]
                  shutil.copy(os.path.join(srcdir, oname), os.path.join(dl_dir, dname))
                  self.cfg['param'][key] = os.path.join('dl', dname)

        return
    
    def download_cfg_from_url(self, cfgfileURL, destdir):
        """
        download the configuration from an url.
        The references to local files are meaningless, 
        so the paths are completed (if necessary) to build an url
        the paths are eliminated
        When we are downloading a configuration file, 
        then all the files should also be downloaded
        """
        from myUtil import *
        import urlparse
        import os

        # create download directory if does not exist
        dl_dir = os.path.join(destdir,'dl')
        if not os.path.exists(dl_dir):
           os.mkdir(dl_dir)

        # DEFAULT PARAM
        self.cfg['param'] = self.default_param.copy()

        # LOAD param.cfg
        # TODO : must be done with eval , MAYBE SOME OTHER SOLUTION?
        self.log("downloading "+ cfgfileURL)
        (localdir, localname) = download(dl_dir, cfgfileURL)
        f = file( os.path.join(localdir ,localname) ); 
        params = eval(f.read()); 
        f.close()

        # Load self.cfg with non-null params
        for key in self.VALID_KEYS:
           if key in params.keys():
              self.cfg['param'][key] = params[key];
           else:
              if key not in self.cfg['param'].keys():
                 self.cfg['param'][key]='' 

        # Prepare the URL's of the files to download
        for key in self.FILE_KEYS:
            if key in params.keys():
               if params[key] != '':
                  # COMPLETE THE URL FOR THE FILES IF NECESSARY
                  self.cfg['param'][key+'_url'] = urlparse.urljoin(cfgfileURL,params[key]) 
                  self.cfg['param'][key] = ''

        return
    
    def download_remaining_url_files(self, destdir):
        """
        download the URL FILES for the images that are not present 
        """
        from myUtil import * 
        import os

        # create download directory if does not exist
        dl_dir = os.path.join(destdir,'dl')
        if not os.path.exists(dl_dir):
           os.mkdir(dl_dir)

        params=self.cfg['param']

        # DOWNLOAD THE FILES 
        for key in self.FILE_KEYS:
            if key in params.keys():
               if params[key] == '' and (key+'_url' in params) and params[key+'_url'] != '':
                  # DOWNLOAD THE FILE AND RENAME IT
                  self.log("downloading "+ params[key+'_url'] )
                  (localdir, localname) = download(dl_dir, params[key+'_url'])

                  oname = localname
                  dname = key + os.path.splitext(oname)[1]
                  shutil.move(os.path.join(localdir, oname), os.path.join(localdir, dname))
                  self.cfg['param'][key] = os.path.join('dl', dname)

        return
    
######### END INPUT HANDLING #################################################################
##############################################################################################

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
            sizeY=image(self.work_dir + 'left_image.png').size[1]
            return self.tmpl_out("params.html", sizeY=sizeY)

        elif action:
            # The crop is done, go to the parameters page
            sizeY=image(self.work_dir + 'left_image.png').size[1]
            return self.tmpl_out("params.html", sizeY=sizeY)
        
        else:
            # The user has not defined all the corners yet
            x = int(x)
            y = int(y)
            
            # Case 1 : nothing is defined
            if (not self.cfg['param'].has_key('x0')):
                
                self.cfg['param']['x0'] = x
                self.cfg['param']['y0'] = y
                
                # draw a cross at the first corner
                plot_cross(self.work_dir + 'left_image.png', x, y, \
                           self.work_dir + 'left_image_corner.png')
                
                # change the page
                return self.tmpl_out("crop.html", corners=1)
            
            # Case 2 : 1 corner is defined in the first image
            elif (not self.cfg['param'].has_key('x1')):

                self.cfg['param']['x1'] = x
                self.cfg['param']['y1'] = y
                
                # draw selection rectangle on the image
                x0 = self.cfg['param']['x0']
                y0 = self.cfg['param']['y0']
                plot_rectangle(self.work_dir + 'left_image.png', x0, y0, x, y, \
                               self.work_dir + 'left_image_selection.png')
                
                # crop from the first input image
                crop_image(self.work_dir + 'left_image.png', x0, y0, x, y, \
                           self.work_dir + 'left_image.png')
                # Same with tiff
                crop_image(self.work_dir + 'left_image.tif', x0, y0, x, y, \
                           self.work_dir + 'left_image.tif')
               
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
                plot_rectangle(self.work_dir + 'right_image.png', x, y2, x3, y3, \
                               self.work_dir + 'right_image_selection.png')
                
                # crop from the first input image
                crop_image(self.work_dir + 'right_image.png', x, y2, x3, y3, \
                           self.work_dir + 'right_image.png')
                # Same with tiff
                crop_image(self.work_dir + 'right_image.tif', x, y2, x3, y3, \
                           self.work_dir + 'right_image.tif')
                
                return self.tmpl_out("crop.html", corners=3)
            return


    @cherrypy.expose
    @init_app
    def wait_single_value(self, shear=None, tilt=None, win=None, 
                          disp_min=None, disp_max=None, subpixel=None):
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
            subpixel = int(subpixel)
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
        self.cfg['param']['subpixel'] = subpixel
        self.cfg['param']['width'] = image(self.work_dir+'right_image.png').size[0]
        self.cfg.save()

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        sizeY=image(self.work_dir + 'left_image.png').size[1]
        return self.tmpl_out("wait.html", sizeY=sizeY)
    
    @cherrypy.expose
    @init_app
    def wait_multiple_values(self, shear_min=None, shear_max=None, shear_nb=None,
                             tilt_min=None, tilt_max=None, tilt_nb=None,
                             win=None, disp_min=None, disp_max=None, subpixel=None):
        """
        params handling and run redirection
        """
        try:
            # The shear has to be between -1 and 1
            shear_min = max(float(shear_min),-1)
            shear_max = min(float(shear_max),1)
            shear_nb = int(shear_nb)
            tilt_min = float(tilt_min)
            tilt_max = float(tilt_max)
            tilt_nb = int(tilt_nb)
            win_w = int(win)
            win_h = int(win)
            disp_min = int(disp_min)
            disp_max = int(disp_max)
            subpixel = int(subpixel)
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
        self.cfg['param']['subpixel'] = subpixel
        self.cfg['param']['width'] = image(self.work_dir+'right_image.png').size[0]
        self.cfg.save()

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        sizeY=image(self.work_dir + 'left_image.png').size[1]
        return self.tmpl_out("wait.html",sizeY=sizeY)


    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """        
        # run the algorithm
        try:
            run_time = time.time()
            if (self.cfg['param']['type'] == 'single'):
                self.run_algo_simple()
            elif (self.cfg['param']['type'] == 'multiple'):
                self.run_algo_multiple()
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        
        # archive



    def run_algo_simple(self):
        """
        Computes the block_matching, on both the normal pair and the transformed pair
        """
        # Parameters reading (we need them to compute the disparity range)
        tilt = self.cfg['param']['tilt']
        disp_min = self.cfg['param']['disp_min']
        disp_max = self.cfg['param']['disp_max']
        width = self.cfg['param']['width']
             
        # Computation of the disparity range needed        
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
        f.write('subpixel='+str(self.cfg['param']['subpixel'])+'\n')
        f.close();
        
        # Computes tilt and shear on the right image
        new_width = int(tilt*width)
        p_transform = self.run_proc(['/bin/bash', 'run_transform.sh', str(new_width)])
        self.wait_proc(p_transform, timeout=self.timeout)

        # Run flat-patches first because it does not depend on disp maps
        p_flat = self.run_proc(['/bin/bash', 'run_flat.sh'])
        self.wait_proc(p_flat, timeout=self.timeout)

        # Block-matching on the two pairs
        p_normal = self.run_proc(['/bin/bash', 'run_n.sh'])
        p_transformed = self.run_proc(['/bin/bash', 'run.sh'])
        self.wait_proc(p_normal, timeout=self.timeout)
        self.wait_proc(p_transformed, timeout=self.timeout)


    def run_algo_multiple(self):
        """
        Computes the block_matching, on the whole set of simulated pairs        
        """

        # read the parameters
        shear_min = self.cfg['param']['shear_min']
        shear_max = self.cfg['param']['shear_max']
        shear_nb = self.cfg['param']['shear_nb']
        tilt_min = self.cfg['param']['tilt_min']
        tilt_max = self.cfg['param']['tilt_max']
        tilt_nb = self.cfg['param']['tilt_nb']
        disp_min = self.cfg['param']['disp_min']
        disp_max = self.cfg['param']['disp_max']
        width = self.cfg['param']['width']
        
        # WRITE THE CONFIG FILE
        f = open(os.path.join(self.work_dir,'params'), 'w')
        f.write('win_w='+str(self.cfg['param']['win_w'])+'\n')
        f.write('win_h='+str(self.cfg['param']['win_h'])+'\n')
        f.write('disp_min='+str(self.cfg['param']['disp_min'])+'\n')
        f.write('disp_max='+str(self.cfg['param']['disp_max'])+'\n')
        f.write('tilt_min='+str(self.cfg['param']['tilt_min'])+'\n')
        f.write('tilt_max='+str(self.cfg['param']['tilt_max'])+'\n')
        f.write('shear_min='+str(self.cfg['param']['shear_min'])+'\n')
        f.write('shear_max='+str(self.cfg['param']['shear_max'])+'\n')
        f.write('subpixel='+str(self.cfg['param']['subpixel'])+'\n')
        f.write('height='+str(image(self.work_dir + 'left_image.png').size[1])+'\n')

        f.close();
        
        # List of tilts, shears
        if tilt_nb>1 :
            tilt_delta = abs(tilt_max-tilt_min)/(tilt_nb-1)
            tilt_list = []
            i = 0
            while (i<tilt_nb):
                tilt = tilt_min + i*tilt_delta
                tilt_list.append(tilt)
                i += 1
        else:
            tilt_list = [tilt_min]
        self.cfg['param']['tilt_list'] = tilt_list
            
        if shear_nb>1 :
            shear_delta = abs(shear_max-shear_min)/(shear_nb-1)
            shear_list = []
            i = 0
            while (i<shear_nb):
                shear = shear_min + i*shear_delta
                shear_list.append(shear)
                i += 1
        else:
            shear_list = [shear_min]
        self.cfg['param']['shear_list'] = shear_list
        self.cfg.save()
        
        # List of disparity range needed
        ############################### TO DO : correct the formula to take shear into account #################################"
        disp_bounds = {}
        for t in tilt_list:
            for s in shear_list:
                if t < 1:
                    d_m = (t-1)*width+t*disp_min
                    d_M = t*disp_max
                else:
                    d_m = t*disp_min
                    d_M = (t-1)*width+t*disp_max
                disp_bounds[t,s] = (d_m, d_M)
        
        # Compute all the deformed right images: first all the tilted images,
        # then we apply shears on these tilted images
        p = {}
        for t in tilt_list:
            t_str = '%1.2f' % t
            p[t] = self.run_proc(['/bin/bash', 'run_tilt.sh', t_str, str(int(t*width))])
        for t in tilt_list:
            self.wait_proc(p[t], timeout=self.timeout)

        for t in tilt_list:
            t_str = '%1.2f' % t
            for s in shear_list:
                s_str = '%1.2f' % s
                p[t,s] = self.run_proc(['/bin/bash', 'run_shear.sh', t_str, s_str])
        for t in tilt_list:
            for s in shear_list:
                self.wait_proc(p[t,s], timeout=self.timeout)
        
        
        # Do the block-matching and filtering on all the simulated pairs
        for t in tilt_list:
            t_str = '%1.2f' % t
            for s in shear_list:
                s_str = '%1.2f' % s
                (d_m,d_M) = disp_bounds[t,s]
                p[t,s] = self.run_proc(['/bin/bash', 'run_multi.sh', t_str, s_str, str(d_m), str(d_M)])
        for t in tilt_list:
            for s in shear_list:
                self.wait_proc(p[t,s], timeout=self.timeout)
                
        # Merge the maps
        p_merge = self.run_proc(['/bin/bash', 'run_merge.sh'])
        self.wait_proc(p_merge, timeout=self.timeout)
        
        # Generate 3D rendering
        p_rendering = self.run_proc(['/bin/bash', 'run_render.sh'])
        self.wait_proc(p_rendering, timeout=self.timeout)
        
#        # Cleanup the tmp dir
        p_clean = self.run_proc(['/bin/bash', 'run_clean.sh'])
        self.wait_proc(p_clean, timeout=self.timeout)


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        sizeY=image(self.work_dir + 'left_image.png').size[1]
        
        if (self.cfg['param']['type'] == 'single'):
            return self.tmpl_out("result_simple.html", sizeY=sizeY)
        elif (self.cfg['param']['type'] == 'multiple'):
            return self.tmpl_out("result_multiple.html", sizeY=sizeY)
    
    
    
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
        for fname in fnames:
            shutil.copy(old_work_dir + fname,
                        self.work_dir + fname)
        # copy cfg
        self.cfg['meta'].update(old_cfg_meta)
        self.cfg.save()
        return
    
# Overwrite of the input_select method to allow better input handling
    @cherrypy.expose
    def input_select(self, **kwargs):
        """
        After this method has run, the images have been:
        downloaded, converted and renamed to standard names
        IF the ground truth is provided, then the mask images
        are also generated
        The format for the images is PNG, except for the ground truth, which is encoded as TIFF
        A PNG thumbnail of the ground truth is also generated
        """
        from lib import config
        import urlparse
        
        self.new_key()
        self.init_cfg()
        
        # get parameters for the preconfigured experiments
        # kwargs contains input_id.x and input_id.y
        # The html form uses the input identifiers as names of the field
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]
        
        # load the input.cfg either from a local path or from an url
        input_cfg_path = config.file_dict(self.input_dir)[input_id]['path']
        
        if urlparse.urlparse(input_cfg_path).netloc == '':
            # it should be a relative path
            cfg_path_or_url = os.path.join(self.base_dir,'input',input_cfg_path , 'param.cfg')
            self.copy_cfg_from_path(cfg_path_or_url,  self.work_dir)
        else: 
           # it is an url
           cfg_path_or_url = urlparse.urljoin(input_cfg_path , 'param.cfg')
           self.download_cfg_from_url(cfg_path_or_url, self.work_dir)
    
        # download the files_url, that may be left from both cases
        self.download_remaining_url_files(self.work_dir)
    
        # process the input files
        msg = self.process_input_files()
    
    
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['input_id'] = input_id
        self.cfg['meta']['original'] = False
        self.cfg.save()
        # jump to the params page
        return self.params(msg=msg, key=self.key)
    
    
    def process_input_files(self):
        """
        PROCESS THE INPUT DATA
         * convert the files to TIFF and generate PNG previews, save with uniform names
         * apply data scaling to the groud truth 
         * update the names in the configuration file
         * generate thumbnail for the ground truth
        """
        msg = None
        import Image


        # CONVERT FORMAT OF THE INPUT FILES
        for file in self.FILE_KEYS:
           localname = self.cfg['param'][file]

           print file

           try:
              print localname
              if localname != '':
                 # Convert and uniformize names
#                 print os.path.join(self.work_dir, localname)
                 if file == 'ground_truth':
                    mindisp = self.cfg['param']['min_disparity']
                    maxdisp = self.cfg['param']['max_disparity']
                    aval    = self.cfg['param']['scale_gt_a']
                    bval    = self.cfg['param']['scale_gt_b']

                    # convert the original image and apply the stretching 
                    #tmp = self.run_proc(['convert.sh', localname , file+'.tif'])
                    tmp = self.run_proc(['axpb.sh',localname, file+'.tif', str(aval), str(bval)])
                    self.wait_proc(tmp)

                    # then remove the original file
                    os.unlink(os.path.join(self.work_dir, localname))

                    # generate the preview with a scale
                    tmp = self.run_proc(['genpreview_stretch.sh', file+'.tif', file+'.png', str(mindisp), str(maxdisp)])
                    self.wait_proc(tmp)

                    # update the configuration
                    self.cfg['param'][file]=file+'.tif'
                    self.cfg['param'][file+'_url']=self.work_url + file+'.tif'
                 else:
                    # read and remove the original file
                    tmp = self.run_proc(['convert.sh', localname , file+'.tif'])
                    self.wait_proc(tmp)
                    os.unlink(os.path.join(self.work_dir, localname))

                    # generate the preview
                    tmp = self.run_proc(['genpreview.sh', file+'.tif', file+'.png'])
                    self.wait_proc(tmp)

#                    im=Image.open(os.path.join(self.work_dir , localname))

                    # update the configuration
                    self.cfg['param'][file]=file+'.tif'
                    self.cfg['param'][file+'_url']=self.work_url + file+'.tif'


           except NameError:
              raise cherrypy.HTTPError(400, # Bad Request
                                      "Bad input file (not found)")
           except IOError:
              raise cherrypy.HTTPError(400, # Bad Request
                                      "Bad input file (not recognized)")


        # CHECK IF THERE ARE TWO IMAGES
        if ( self.cfg['param']['left_image'] == '' or self.cfg['param']['right_image'] == '' ):
            raise cherrypy.HTTPError(400, # Bad Request
                  "Stereoscope (noun): a device by which TWO photographs " + 
                  "of the same object taken at slightly different angles " + 
                  "are viewed together, creating an impression of depth and solidity." )

        # determine the image height and width
        im = Image.open(self.work_dir+'left_image.png')
        self.cfg['param']['image_width']  = im.size[0]
        self.cfg['param']['image_height'] = im.size[1]


        # GENERATE DISPARITY THUMBNAIL IF THE DISPARITY IS PROVIDED
        if self.cfg['param']['ground_truth'] != '':
#            # generate thumbnail (already done!)

            # CHECK IF THERE IS A MASK otherwise generate one
            if self.cfg['param']['ground_truth_mask'] == '':
               imw = self.cfg['param']['image_width']
               imh = self.cfg['param']['image_height']
               # generate an empty image and save it
               Image.new('I',(imw, imh), color=255).save(os.path.join(self.work_dir,'ground_truth_mask.png'))
               # update config
               self.cfg['param']['ground_truth_mask'] = 'ground_truth_mask.png'
    
    
