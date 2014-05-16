"""
Semi-Global Matching
"""

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import ctime
from lib.base_app import init_app
import shutil
import cherrypy
from cherrypy import TimeoutError
import os.path
import time


class app(base_app):
    """ SGM demo app """

    title = "Semi-Global Matching"
    input_nb = 2 # number of input images
    input_max_pixels = 1024 * 1024 # max size (in pixels) of an input image
    is_test = True       # switch to False for deployment
    is_listed = True
    xlink_article = 'http://dev.ipol.im/~carlo/ipol_demo_testing/sgm/'

    def _build_rectify(self):
        """
        build/update of rectify program
        """
                # store common file path in variables
        rectify_tgz_file = self.dl_dir + "MissStereo.tar.gz"
        rectify_tgz_url = "http://www.ipol.im/pub/pre/78/MissStereo.tar.gz"
        rectify_log_file = self.base_dir + "build_MissStereo.log"
        build_dir = (self.src_dir + os.path.join("MissStereo", "build")
                     + os.path.sep)
        src_bin = dict([(build_dir + os.path.join("bin", prog),
                         self.bin_dir + prog)
                        for prog in ["homography", "orsa", "rectify",
                                     "sift", "size", "showRect"]])
        src_bin[self.src_dir
                + os.path.join("MissStereo","scripts","Rectify.sh")] \
                               = os.path.join(self.bin_dir, "Rectify.sh")
        build.download(rectify_tgz_url, rectify_tgz_file)
        if all([(os.path.isfile(bin_file) and
                 ctime(rectify_tgz_file) < ctime(bin_file))
                for bin_file in src_bin.values()]):
            cherrypy.log("no rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(rectify_tgz_file, self.src_dir)
            # build the program
            os.mkdir(build_dir)
            build.run("cmake -D CMAKE_BUILD_TYPE:string=Release ../src",
                      stdout=rectify_log_file, cwd=build_dir)
            build.run("make -C %s homography orsa rectify showRect sift size"
                      % build_dir, stdout=rectify_log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            for (src, dst) in src_bin.items():
                shutil.copy(src, dst)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)

    def build(self):
        """
        program build/update
        """
        #TODO: add automatic compilation of iion, qauto, plambda and disp_statistics
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        #self._build_rectify()

        git_repo = "https://carlodef@bitbucket.org/carlodef/sgm.git"
        build_dir = os.path.join(self.src_dir, "src")
        prog_file = os.path.join(self.bin_dir, "sgm")
        log_file = os.path.join(self.base_dir, "build.log")

        # Update or import the code from git repository
        if os.path.isdir(self.src_dir):
            os.chdir(self.src_dir)
            os.system("git pull")
            os.chdir(self.base_dir)
        else:
            os.system("git clone --depth 1 %s %s" % (git_repo, self.src_dir))

        # build the program and copy it to the bin dir
        build.run("make -j -C %s all" % build_dir, stdout=log_file)
        shutil.copy(os.path.join(build_dir, "sgm"), prog_file)

        # copy scripts to bin dir
        import glob
        for file in glob.glob(os.path.join(self.base_dir, 'scripts/*')):
            shutil.copy(file, self.bin_dir)
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


    #
    # INDEX
    #

    @cherrypy.expose
    def index(self):
        """
        demo presentation and input menu
        """
        # read the input index as a dict
        inputd = config.file_dict(self.input_dir)
        tn_size = int(cherrypy.config.get('input.thumbnail.size', '192'))
        # TODO: build via list-comprehension
        for (input_id, input_info) in inputd.items():
            # convert the files to a list of file names
            # by splitting at blank characters
            # and generate thumbnails and thumbnail urls
            fname = input_info['files'].split()
#           GENERATE THUMBNAIL EVEN FOR FILES IN SUBDIRECTORIES OF INPUT
            inputd[input_id]['tn_url'] = [self.input_url +'/'+ os.path.dirname(f) + '/' +
                        os.path.basename(thumbnail(self.input_dir + f, (tn_size, tn_size)))
                        for f in fname]
            inputd[input_id]['url'] = [self.input_url + os.path.basename(f)
                                       for f in fname]
#            tn_fname = [thumbnail(self.input_dir + f, (tn_size, tn_size))
#                        for f in fname]
#            inputd[input_id]['url'] = [self.input_url + os.path.basename(f)
#                                       for f in fname]
#            inputd[input_id]['tn_url'] = [self.input_url + os.path.basename(f)
#                                          for f in tn_fname]


        return self.tmpl_out("input.html",
                             inputd=inputd)



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
                 'run', 'input_data_url', 'input_data', 'subpixel' , 'preprocess',
                 'tilt_min', 'tilt_max', 'tilt_nb',
                 'shear_min', 'shear_max', 'shear_nb'
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
             'subpixel' : 1,
             'tilt_min' : 0.7,
             'tilt_max' : 1.3,
             'tilt_nb' : 3,
             'shear_min' : -0.2,
             'shear_max' : 0.2,
             'shear_nb' : 3
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
            if (key in params.keys() and str(params[key]) is not ""):
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
        import myUtil
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
        (localdir, localname) = myUtil.download(dl_dir, cfgfileURL)
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
        import myUtil
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
                  (localdir, localname) = myUtil.download(dl_dir, params[key+'_url'])

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
                    tmp = self.run_proc(['save_png.sh', file+'.tif', file+'.png', str(mindisp), str(maxdisp)])
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
#   Les methodes input_select et input_upload
#   renvoient a la methode params, qui affiche la page params.html.
    def params(self, msg=None, newrun=False):
        """
        Redirects to the params page
        """
        if newrun:
            self.clone_input()

        return self.tmpl_out("paramresult.html")


    def write_config_file_for_shell(self, config_dict):
        """
        Writes the config file used by the shell scripts
        """
        f = open(os.path.join(self.work_dir, 'params'), 'w')
        f.write('min_disparity=' + str(config_dict['param']['min_disparity']) + '\n')
        f.write('max_disparity=' + str(config_dict['param']['max_disparity']) + '\n')
        f.write('lr=' + str(config_dict['param']['lr']) + '\n')
        f.write('nb_iter=' + str(config_dict['param']['nb_iter']) + '\n')
        f.write('P1=' + str(config_dict['param']['P1']) + '\n')
        f.write('P2=' + str(config_dict['param']['P2']) + '\n')
        f.write('ground_truth=' + str(config_dict['param']['ground_truth']) + '\n')
        f.close();


    @cherrypy.expose
    @init_app
    def wait(self, min_disparity=None, max_disparity=None, lr=None,
            nb_iter=None, P1=None, P2=None):
        """
        params handling and run redirection
        """
        try:
            min_disparity = float(min_disparity)
            max_disparity = float(max_disparity)
            lr = float(lr)
            nb_iter = int(nb_iter)
            P1 = float(P1)
            P2 = float(P2)
        except ValueError:
            return self.error(errcode='badparams',
                              errmsg="The parameters must be numeric.")

        self.cfg['param']['min_disparity'] = min_disparity
        self.cfg['param']['max_disparity'] = max_disparity
        self.cfg['param']['lr'] = lr
        self.cfg['param']['nb_iter'] = nb_iter
        self.cfg['param']['P1'] = P1
        self.cfg['param']['P2'] = P2
        self.cfg.save()
        self.write_config_file_for_shell(self.cfg)

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html",sizeY=self.cfg['param']['image_height'])



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
            self.cfg['param']['run'] = 'done'
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'zip_results?key=%s' % self.key)
        #http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive


    def run_algo(self):
        """
        Launches the run_sgm.sh script, and then the statistics script.
        """
        #p_angulo = self.run_proc(['batch_angulo.py'])
        #self.wait_proc(p_angulo, timeout=self.timeout)

        #p_refinement = self.run_proc(['/bin/bash','batch_refinement.sh', self.key])

        p = self.run_proc(['/bin/bash','run_sgm.sh'])
        self.wait_proc(p, timeout=self.timeout)

        if self.cfg['param']['ground_truth'] != '':
            p_stat = self.run_proc(['/bin/bash','compute_statistics.sh'])
            self.wait_proc(p_stat, timeout=self.timeout)


    def merge_png(self,out,in1,in2):
        """
        From png images in1 and in2 (u2 being transparent), makes an unique image with in2 on top of in1
        """
        import Image
        background = Image.open(self.work_dir + in1)
        foreground = Image.open(self.work_dir + in2)

        background_rgb = background.convert('RGB')
        background_rgb.paste(foreground, (0, 0), foreground)
        background_rgb.save(out)
        return

    @cherrypy.expose
    @init_app
    def zip_results(self):
        """
        zip the tif images in a single downloadable archive:
        left_image.tif
        right_image.tif
        disp_sgm.tif
        """
        # Put the files in a zip
        pr = self.run_proc(['/bin/bash', 'zip_results.sh'])
        self.wait_proc(pr, timeout=self.timeout)

        # Go back on the result page
        http.redir_303(self.base_url + 'result?key=%s' % self.key)


    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        # go on the results page
        return self.tmpl_out("paramresult.html")


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
