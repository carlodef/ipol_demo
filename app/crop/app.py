from lib import base_app, http
from lib.base_app import init_app
import cherrypy
import os.path
import shutil
from lib import config
from utils import *

class app(base_app):
    """ Crop """

    title = 'Crop tool for stereo pairs'
    
    input_nb = 2 # number of input images
    input_max_pixels = 10000 * 10000 # max size (in pixels) of an input image
    input_max_weight = 3 * 10000 * 10000 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png'   # input image expected extension (ie file format)
    timeout = 60
    is_test = True       # switch to False for deployment
    is_listed = True


    def build(self):
        """
        program build/update
        """
        # Create bin dir (delete the previous one if exists)
        if os.path.isdir(self.bin_dir):
            shutil.rmtree(self.bin_dir)
        os.mkdir(self.bin_dir)
        
        # link all the scripts to the bin dir
        import glob
        for file in glob.glob( os.path.join( self.base_dir, 'scripts/*')):
            os.symlink(file, os.path.join( self.bin_dir , os.path.basename(file)))
    
        # Needed binaries
        BINARIES=[ 'iion', 'qauto', 'plambda']
        for file in BINARIES:
            shutil.copy(os.path.join(self.base_dir,'../answer_old_question/bin/'+file),self.bin_dir) 
        return


    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

    
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
                 'run', 'input_data_url', 'input_data', 'preprocess',
                 ]

    # these are files 
    FILE_KEYS=[ 'left_image', 'right_image', 'ground_truth', 'ground_truth_mask', 'ground_truth_occ', 'input_data']

    # Default parameters
    default_param = dict(
          {  'min_disparity': -31,
             'max_disparity': 31,
             'image_width': 800,
             'image_height': 600,
             'scale_gt_a' : 1,
             'scale_gt_b' : 0,
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
        
        # jump to the crop page
        return self.crop(key=self.key)
    
    
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

   
######### END INPUT HANDLING AND PROCESSING ##################################################
##############################################################################################


    @cherrypy.expose
    @init_app
    def crop(self, done=None, x=None, y=None):
        """
        select a rectangle in the image
        """
        if done:
            # The crop is done, go to the results page
            http.redir_303(self.base_url + 'zip_results?key=%s' % self.key)
        
        elif (x == None):
            # the user has not yet clicked on the first corner
            return self.tmpl_out("crop.html", corners=0)            

        else:
            # The user has clicked, but not all the corners are defined yet      
            x = int(x)
            y = int(y)
                  
            # Case 1 : first corner clicked, but nothing stored
            if (not self.cfg['param'].has_key('x0')):
                
                self.cfg['param']['x0'] = x
                self.cfg['param']['y0'] = y
                
                # draw a cross at the first corner
                plot_cross(self.work_dir + 'left_image.png', x, y, \
                           self.work_dir + 'left_image_corner.png')
                
                # change the page
                return self.tmpl_out("crop.html", corners=1)
            
            # Case 2 : 1 corner stored, the second has been clicked
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
                           self.work_dir + 'out_0.png')
                crop_image(self.work_dir + 'left_image.tif', x0, y0, x, y, \
                           self.work_dir + 'out_0.tif')
               
                return self.tmpl_out("crop.html", corners=2)
             
            # Case 3 : 2 corners defined, the third is clicked
            else:
                x0 = self.cfg['param']['x0']
                y0 = self.cfg['param']['y0']
                x1 = self.cfg['param']['x1']
                y1 = self.cfg['param']['y1']
                y2 = min(y0, y1)
                self.cfg['param']['x2'] = x
                self.cfg['param']['y2'] = y2
                x3 = x + abs(x1 - x0)
                y3 = y2 + abs(y1 - y0)    

                # draw selection rectangle on the image
                plot_rectangle(self.work_dir + 'right_image.png', x, y2, x3, y3, \
                               self.work_dir + 'right_image_selection.png')
                
                # crop from the first input image
                crop_image(self.work_dir + 'right_image.png', x, y2, x3, y3, \
                           self.work_dir + 'out_1.png')
                crop_image(self.work_dir + 'right_image.tif', x, y2, x3, y3, \
                           self.work_dir + 'out_1.tif')

                # crop from the ground truth map and mask
                if self.cfg['param']['ground_truth'] != '':
                    crop_image(self.work_dir + 'ground_truth.tif', x, y2, x3, y3, \
                           self.work_dir + 'out_gt.tif')
                    crop_image(self.work_dir + 'ground_truth_mask.tif', x, y2, x3, y3, \
                           self.work_dir + 'out_gt_mask.tif')

                return self.tmpl_out("crop.html", corners=3)
        return
            
    @cherrypy.expose
    @init_app
    def zip_results(self):
        """
        zip the output images in a single downloadable archive:
        out_0.tif
        out_1.tif
        out_gt.tif
        """
        # Put the files in a zip 
        pr = self.run_proc(['/bin/bash', 'zip_results.sh'])
        self.wait_proc(pr, timeout=self.timeout)
        
        sizeY = image(self.work_dir + 'out_0.png').size[1]
        return self.tmpl_out("results.html", sizeY=sizeY)
