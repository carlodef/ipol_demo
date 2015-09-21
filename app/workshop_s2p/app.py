"""
s2p ipol demo
"""

import os.path
import shutil
import time
import numpy as np
import glob
import json
import ast
import cherrypy
from cherrypy import TimeoutError

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import app_expose, ctime
from lib.base_app import init_app

import utils


class app(base_app):
    """
    s2p ipol demo
    """

    title = "s2p: Satellite Stereo Pipeline"
    xlink_article = 'http://dev.ipol.im/~carlo/s2p_papers'

    input_nb = 2 # number of input images
    input_img_max_weight = 100 * 1024 * 1024 # max size (in bytes) of an input file
    input_rpc_max_weight = 2 * 1024 * 1024 # max size (in bytes) of an input file
    input_tot_max_weight = 100 * 1024 * 1024 # max size (in bytes) of an input file
    is_test = True       # switch to False for deployment


    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        app_expose(base_app.index)


    def build(self):
        """
        program build/update
        """
        log_file = self.base_dir + "build.log"

        s2p_dir = os.path.join(self.base_dir, 's2p_src')

        # update local copy of s2p source
        if not os.path.isdir(s2p_dir):
            print 's2p_src directory not found, doing a git clone'
            cmd = ("git clone --depth 1 https://carlodef@bitbucket.org/"
                   "carlodef/s2p.git %s" % s2p_dir)
            os.system(cmd)
        else:
            print 's2p_src directory found, doing a git pull'
            os.system("cd %s && git pull && cd -" % s2p_dir)


        # compile s2p 'c' folder
        try:
            build.run("make -j -C %s" % s2p_dir, stdout=log_file)
        except RuntimeError:
            print 'build failed (see log file)'

        # Create bin dir (delete the previous one if exists)
        if os.path.isdir(self.bin_dir):
            shutil.rmtree(self.bin_dir)
        os.mkdir(self.bin_dir)

        # copy scripts and s2p.py to bin dir
        for file in glob.glob(os.path.join(self.base_dir, 'scripts/*')):
            shutil.copy(file, self.bin_dir)
        shutil.copy(os.path.join(s2p_dir, 's2p.py'), self.bin_dir)

        # make links to s2p_dir/bin and s2p_dir/python in the self.bin_dir folder
        os.symlink(os.path.join(s2p_dir, 'bin'), os.path.join(self.bin_dir,
            'bin'))
        os.symlink(os.path.join(s2p_dir, 'python'), os.path.join(self.bin_dir,
            'python'))

        # link to pleiades data
        if not os.path.lexists(os.path.join(self.input_dir, 'data')):
            os.symlink(os.path.join(os.path.expanduser("~"), 's2p_demo_data'),
                os.path.join(self.input_dir, 'data'))

        return


    @cherrypy.expose
    @init_app
    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        # When we arrive here, self.key should be empty.
        # If not, it means that the execution belongs to another thread
        # and therefore we need to reuse the app object
        key_is_empty = (self.key == "")
        if key_is_empty:
            # New execution: create new app object
            self2 = base_app(self.base_dir)
            self2.__class__ = self.__class__
            self2.__dict__.update(self.__dict__)
        else:
            # Already known execution
            self2 = self

        self2.new_key()
        self2.init_cfg()

        # Add app to object pool
        if key_is_empty:
            pool = AppPool.get_instance() # Singleton pattern
            pool.add_app(self2.key, self2)

        # get the dataset id
        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]

        # read the dictionary of inputs
        input_dict = config.file_dict(self.input_dir)

        # create symlinks to the full images and rpc files. There must be the
        # same number of image files and rpc files. The number of previews
        # doesn't matter.
        img_files = input_dict[input_id]['tif'].split()
        rpc_files = input_dict[input_id]['rpc'].split()
        assert len(img_files) == len(rpc_files)

        img_files_abs = [os.path.join(self.input_dir, f) for f in img_files]
        rpc_files_abs = [os.path.join(self.input_dir, f) for f in rpc_files]
        for i in range(len(img_files)):
            os.symlink(img_files_abs[i], os.path.join(self.work_dir,
                'img_%02d.tif' % (i+1)))
            os.symlink(rpc_files_abs[i], os.path.join(self.work_dir,
                'rpc_%02d.xml' % (i+1)))

        # if it's an xs dataset, create a link to the clr reference image
        if 'clr' in input_dict[input_id]:
            clr_files = input_dict[input_id]['clr'].split()
            clr_files_abs = [os.path.join(self.input_dir, f) for f in clr_files]
            os.symlink(img_files_abs[0], os.path.join(self.work_dir, 'img_01_clr.tif'))

        # link to the preview files, needed by the archive
        prv_files = input_dict[input_id]['files'].split()
        prv_files_abs = [os.path.join(self.input_dir, f) for f in prv_files]
        for i, f in enumerate(prv_files_abs):
            os.symlink(f, os.path.join(self.work_dir, 'prv_%02d.png' % (i+1)))

        # save params of the dataset
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg['meta']['input_id'] = input_id
        self.cfg['meta']['nb_img'] = len(img_files)
        self.cfg['meta']['color'] = input_dict[input_id]['color']

        # either one of the two keys dzi8 or dzi16 must exist
        self.cfg['param']['tif_paths'] = input_dict[input_id]['tif'].split()
        if input_dict[input_id].has_key('dzi8'):
            self.cfg['param']['dzi_paths'] = input_dict[input_id]['dzi8'].split()
        else:
            self.cfg['param']['dzi_paths'] = input_dict[input_id]['dzi16'].split()
        self.cfg.save()

        # jump to the display page
        return self.params(key=self.key)


    @cherrypy.expose
    @init_app
    def input_upload(self, **kwargs):
        """
        upload images and rpcs
        """
        # When we arrive here, self.key should be empty.
        # If not, it means that the execution belongs to another thread
        # and therefore we need to reuse the app object
        key_is_empty = (self.key == "")
        if key_is_empty:
            # New execution: create new app object
            self2 = base_app(self.base_dir)
            self2.__class__ = self.__class__
            self2.__dict__.update(self.__dict__)
        else:
            # Already known execution
            self2 = self

        self2.new_key()
        self2.init_cfg()

        # Add app to object pool
        if key_is_empty:
            pool = AppPool.get_instance() # Singleton pattern
            pool.add_app(self2.key, self2)

        # receive the input files
        for i in range(2):
            img_up = kwargs['img_%i' % (i+1)]
            if not img_up.filename:
                raise cherrypy.HTTPError(400, "Missing input file")
            extension = os.path.splitext(img_up.filename)[1].lower()
            if not extension in ['.tif', '.tiff']:
                raise cherrypy.HTTPError(400, "image files must be TIFF")
            img_save = file(self.work_dir + 'img_%02d.tif' % (i+1), 'wb')
            size = 0
            while True:
                data = img_up.file.read(8192)
                if not data:
                    break
                size += len(data)
                if size > self.input_img_max_weight:
                    raise cherrypy.HTTPError(400, ("Image File too large,"
                        "resize or use better compression"))
                img_save.write(data)
            img_save.close()

            rpc_up = kwargs['rpc_%i' % (i+1)]
            if not rpc_up.filename:
                raise cherrypy.HTTPError(400, "Missing input file")
            extension = os.path.splitext(rpc_up.filename)[1].lower()
            if not extension in ['.xml', '.txt']:
                raise cherrypy.HTTPError(400, "RPC files must be XML or TXT")
            rpc_save = file("%s/rpc_%02d%s" % (self.work_dir, i+1, extension), 'wb')
            size = 0
            while True:
                data = rpc_up.file.read(128)
                if not data:
                    break
                size += len(data)
                if size > self.input_rpc_max_weight:
                    raise cherrypy.HTTPError(400, "RPC File too large")
                rpc_save.write(data)
            rpc_save.close()

        # create previews
        self.process_input_files()

        # send email to carlo
        os.system("echo %s | mail -s 's2p upload' carlodef@gmail.com" % self.key)

        # save params of the dataset
        self.log("input uploaded")
        self.cfg['meta']['original'] = True
        self.cfg['meta']['input_id'] = 'uploaded'
        self.cfg['meta']['nb_img'] = 2
        self.cfg['meta']['color'] = 'panchro'
        self.cfg.save()

        # jump to the params page
        return self.params(key=self.key)


    def process_input_files(self):
        """
        Process uploaded input data
        * check that images are valid TIFF files (TODO)
        * generates dzi (Deep Zoom Image) for the image files 
        """
        script = os.path.join(self.base_dir, 'scripts',
                              'create_8bits_dzi_from_tiff.sh')
        img1 = os.path.join(self.work_dir, "img_01.tif")
        img2 = os.path.join(self.work_dir, "img_02.tif")
        os.system("/bin/bash %s %s" % (script, img1))
        os.system("/bin/bash %s %s" % (script, img2))
        self.cfg['param']['dzi_paths'] = []
        self.cfg['param']['dzi_paths'].append(os.path.join("tmp", self.key,
            "img_01_8BITS.dzi"))
        self.cfg['param']['dzi_paths'].append(os.path.join("tmp", self.key,
            "img_02_8BITS.dzi"))

    @init_app
    def params(self, newrun=False):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        dzi_paths = ast.literal_eval(self.cfg['param']['dzi_paths'])
        return self.tmpl_out("display.html", list_of_paths_to_dzi_files=dzi_paths)


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        # save the parameters in self.cfg['param']
        nb_img = self.cfg['meta']['nb_img']
        color = self.cfg['meta']['color'] # panchro | panchro_xs | pansharpened
        self.cfg['param']['nb_img'] = nb_img
        self.cfg['param']['color'] = color
        self.cfg['param']['out_dir'] = 's2p_results'
        self.cfg['param']['images'] = [
          { "img" : "img_01.tif",
            "rpc" : "rpc_01.xml" },
          { "img" : "img_02.tif",
            "rpc" : "rpc_02.xml" }
          ]
        if nb_img == 3:
           self.cfg['param']['images'].append({"img" : "img_03.tif",
               "rpc" : "rpc_03.xml"})
        if color == 'panchro_xs':
            self.cfg['param']['images'][0]['clr'] = "img_01_clr.tif"
        self.cfg['param']['roi'] = {}
        self.cfg['param']['roi']['x'] = int(kwargs['x'])
        self.cfg['param']['roi']['y'] = int(kwargs['y'])
        self.cfg['param']['roi']['w'] = int(kwargs['w'])
        self.cfg['param']['roi']['h'] = int(kwargs['h'])
        self.cfg['param']["matching_algorithm"] = str(kwargs['block_match_method'])
        self.cfg['param']['subsampling_factor'] = int(kwargs['zoom'])
        self.cfg['param']["subsampling_factor_registration"] = np.ceil(int(kwargs['zoom']) * 0.5)
        self.cfg['param']["sift_match_thresh"] = 0.4
        self.cfg['param']["disp_range_extra_margin"] = 0.2
        self.cfg['param']["n_gcp_per_axis"] = 5
        self.cfg['param']["epipolar_thresh"] = 0.5
        self.cfg['param']["use_pleiades_unsharpening"] = True
        self.cfg['param']["debug"] = False
        self.cfg['param']["tile_size"] = 1000
        self.cfg['param']["disp_range_method"] = "sift"
        self.cfg['param']["temporary_dir"] = "tmp"
        self.cfg.save()

        # write the parameters in a json file
        fp = open(self.work_dir+'config.json', 'w')
        json.dump(self.cfg['param'], fp, indent=4)
        fp.close()

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
            self.run_algo()
           # self.cfg['param']['run'] = 'done'
           # self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # GENERATE A ZIP (do not wait for it)
        p = self.run_proc(['/bin/bash', 'zipresults.sh'])
#        self.wait_proc(p, timeout=self.timeout)

        # archive: all experiments are archived
        # WARNING: with the new IPOL lib/archive.py, you cannot archive files that are in subdirectories
        ar = self.make_archive()
        ar.add_file("config.json", info="input")
#        ar.add_file("prv_ref.png", "input.png", info="input")
        #ar.add_file("roi_ref_preview.png", info="input")
        #ar.add_file("roi_sec_0_preview.png", info="input")
        #ar.add_file("height_map_preview.png", info="output")
        ar.add_file("rectified_ref_preview.png", info="input")
        ar.add_file("rectified_sec_preview.png", info="input")
        ar.add_file("rectified_disp_preview.png", info="output")
        ar.add_info({"roi": self.cfg['param']['roi'],
                     "input_id": self.cfg['meta']['input_id'],
                     "nb_img": self.cfg['param']['nb_img'],
                     "stereo_algo": self.cfg['param']['matching_algorithm']})
#        if self.cfg['meta']['color'] in ['panchro_xs', 'pansharpened']:
#            ar.add_file("roi_color_ref_preview.png", info="output")
        ar.save()


    def run_algo(self):
        """
        the core algo runner

        could also be called by a batch processor
        this one needs no parameter
        """
#        p = self.run_proc(['helper_convert_inputs.sh', 'config.json', 'prv_01.png'])
#        self.wait_proc(p, timeout=self.timeout)

        run_time = time.time()
        p = self.run_proc(['s2p.sh', 'config.json'])
        self.wait_proc(p, timeout=10*self.timeout)
        self.cfg['info']['run_time'] = time.time() - run_time
        self.cfg.save()

        p = self.run_proc(['helper_convert_outputs.sh'])
        self.wait_proc(p, timeout=self.timeout)

#        p = self.run_proc(['helper_archive.sh', 'config.json'])
#        self.wait_proc(p, timeout=self.timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
#        f = open(os.path.join(self.work_dir, "config.json"))
#        s2p_cfg = json.load(f)
#        f.close()
#        h = int(s2p_cfg['roi']['h'])
        nc, nr = utils.image_size_identify(os.path.join(self.work_dir,
                                                       "rectified_ref_preview.png"))
        return self.tmpl_out("result.html", height=nr)
