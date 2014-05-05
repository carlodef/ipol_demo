"""
s2p ipol demo
"""

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time
import numpy as np

class app(base_app):
    """
    s2p ipol demo
    """

    title = "s2p: Satellite Stereo Pipeline"
    xlink_article = 'http://dev.ipol.im/~carlo/s2p_papers'

    input_nb = 2 # number of input images
    input_img_max_weight = 1024 * 1024 * 1024 # max size (in bytes) of an input file
    input_rpc_max_weight = 2 * 1024 * 1024 # max size (in bytes) of an input file
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
#        app_expose(base_app.index)
#        app_expose(base_app.input_select)
#        app_expose(base_app.input_upload)
        # params() is modified from the template
        app_expose(base_app.params)
        # run() and result() must be defined here

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


        return self.tmpl_out("input.html",
                             inputd=inputd)

    def build(self):
        """
        program build/update
        """
        log_file = self.base_dir + "build.log"

        s2p_dir = os.path.join(self.base_dir, 's2p_src')

        # update local copy of s2p source
        if not os.path.isdir(s2p_dir):
            print 's2p_src directory not found, doing a git clone'
            os.system("git clone --depth 1 https://carlodef@bitbucket.org/carlodef/s2p.git %s" % s2p_dir)
        else:
            print 's2p_src directory found, doing a git pull'
            os.system("cd %s && git pull && cd -" % s2p_dir)


        # compile s2p 'c' folder
        build.run("make -j -C %s/c" % s2p_dir, stdout=log_file)

        # Create bin dir (delete the previous one if exists)
        if os.path.isdir(self.bin_dir):
            shutil.rmtree(self.bin_dir)
        os.mkdir(self.bin_dir)

        # copy scripts and s2p.py to bin dir
        import glob
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
            os.symlink(os.path.join(s2p_dir, 'data'),
                os.path.join(self.input_dir, 'data'))

        return

    @cherrypy.expose
    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        self.new_key()
        self.init_cfg()

        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]

        # get the images
        input_dict = config.file_dict(self.input_dir)
        fnames = input_dict[input_id]['files'].split()
        fnames_absolute = [self.input_url + f for f in fnames]
        nb_img = input_dict[input_id]['nb_img']
        color = input_dict[input_id]['color']
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = True
        self.cfg['meta']['input_id'] = input_id
        self.cfg['meta']['nb_img'] = nb_img
        self.cfg['meta']['color'] = color
        self.cfg.save()

        # jump to the params page
        return self.params(key=self.key, fnames=fnames_absolute)

    @cherrypy.expose
    @init_app
    def input_upload(self, **kwargs):
        """
        upload images and rpcs
        """
        self.new_key()
        self.init_cfg()

        # receive the input files
        print kwargs.keys()
        for i in range(2):
            img_up = kwargs['img_%i' % i]
            if not img_up.filename:
                raise cherrypy.HTTPError(400, "Missing input file")
            extension = os.path.splitext(img_up.filename)[1].lower()
            if not extension in ['.tif', '.tiff']:
                raise cherrypy.HTTPError(400, "image files must be TIFF")
            img_save = file(self.work_dir + 'img_%i.tif' % i, 'wb')
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

            rpc_up = kwargs['rpc_%i' % i]
            if not rpc_up.filename:
                raise cherrypy.HTTPError(400, "Missing input file")
            extension = os.path.splitext(rpc_up.filename)[1].lower()
            if not extension in ['.xml', '.txt']:
                raise cherrypy.HTTPError(400, "RPC files must be XML or TXT")
            rpc_save = file("%s/rpc_%i%s" % (self.work_dir, i, extension), 'wb')
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

        # process the input files, and save informations in the config file
        fnames = self.process_input_files()
        self.log("input uploaded")
        self.cfg['meta']['original'] = True
        self.cfg['meta']['input_id'] = 'unknown'
        self.cfg['meta']['nb_img'] = 2
        self.cfg['meta']['color'] = 'panchro'
        self.cfg.save()

        # jump to the params page
        return self.params(key=self.key, fnames=fnames)


    def process_input_files(self):
        """
        Process uploaded input data
        * check that images are valid TIFF files
        * generates jpg previews of the image files
        """
        import utils
        utils.generate_preview("%s/img_0.tif" % self.work_dir)
        utils.generate_preview("%s/img_1.tif" % self.work_dir)
        return ["%s/img_%d_prv.jpg" % (self.work_url, i) for i in [0, 1]]


    @init_app
    def params(self, fnames=None, newrun=False, msg=None):
        """
        configure the algo execution
        """
        if newrun:
            self.clone_input()
        return self.tmpl_out("params.html", input=fnames)


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        # save the parameters in self.cfg['param']
        input_id = self.cfg['meta']['input_id']
        nb_img = self.cfg['meta']['nb_img']
        color = self.cfg['meta']['color'] # panchro | panchro_xs | pansharpened
        self.cfg['param']['input_id'] = input_id
        self.cfg['param']['nb_img'] = nb_img
        self.cfg['param']['color'] = color
        self.cfg['param']['out_dir'] = 's2p_results'
        if nb_img == 3:
           self.cfg['param']['images'] = [
             { "img" : "data/%s/im02.tif" % input_id,
               "rpc" : "data/%s/rpc02.xml"% input_id },
             { "img" : "data/%s/im01.tif"% input_id,
               "rpc" : "data/%s/rpc01.xml"% input_id },
             { "img" : "data/%s/im03.tif"% input_id,
               "rpc" : "data/%s/rpc03.xml"% input_id }
             ]
        if nb_img == 2:
           self.cfg['param']['images'] = [
             { "img" : "data/%s/im02.tif" % input_id,
               "rpc" : "data/%s/rpc02.xml"% input_id },
             { "img" : "data/%s/im01.tif"% input_id,
               "rpc" : "data/%s/rpc01.xml"% input_id }
             ]
        if color == 'panchro_xs':
            self.cfg['param']['images'][0]['clr'] = "data/%s/im02_color.tif" % input_id
        self.cfg['param']['roi'] = {}
        self.cfg['param']['roi']['w'] = int(kwargs['roi_width'])
        self.cfg['param']['roi']['h'] = int(kwargs['roi_height'])
        self.cfg['param']['roi_preview'] = {}
        self.cfg['param']['roi_preview']['x'] = int(kwargs['x'])
        self.cfg['param']['roi_preview']['y'] = int(kwargs['y'])
        self.cfg['param']["matching_algorithm"] = str(kwargs['block_match_method'])
        self.cfg['param']['subsampling_factor'] = int(kwargs['zoom'])
        self.cfg['param']["subsampling_factor_registration"] = np.ceil(int(kwargs['zoom']) * 0.5)
        self.cfg['param']["sift_match_thresh"] = 0.4
        self.cfg['param']["disp_range_extra_margin"] = 0.2
        self.cfg['param']["n_gcp_per_axis"] = 5
        self.cfg['param']["epipolar_thresh"] = 0.5
        self.cfg['param']["use_pleiades_unsharpening"] = True
        self.cfg['param']["debug"] = False
        self.cfg['param']["preview_coordinate_system"] = True
        self.cfg['param']["tile_size"] = 1000
        self.cfg['param']["disp_range_method"] = "sift"

        self.cfg['meta']["orig"] = True
        self.cfg.save()

        # write the parameters in a json file
        import json
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
        os.symlink(self.input_dir+'/data', self.work_dir+'/data')

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

        # archive
        if self.cfg['meta']['original']:
            ar = self.make_archive()
            ar.add_file("config.json", info="input")
            ar.add_file("input_0.png", "input.png", info="input")
            ar.add_file("dem_preview.png", info="output")
            ar.add_file("roi_ref_preview.png", info="output")
            ar.add_info({"roi": self.cfg['param']['roi'],
                         "input_id": self.cfg['param']['input_id'],
                         "nb_img": self.cfg['param']['nb_img']})
            if self.cfg['meta']['color'] == 'panchro_xs':
                ar.add_file("roi_color_ref_preview.png", info="output")
            if self.cfg['meta']['color'] == 'pansharpened':
                ar.add_file("roi_color_ref_preview.png", info="output")
            ar.save()

        return self.tmpl_out("run.html")

    def run_algo(self):
        """
        the core algo runner

        could also be called by a batch processor
        this one needs no parameter
        """
        p = self.run_proc(['helper_convert_inputs.sh', 'config.json', 'input_0.png'])
        self.wait_proc(p, timeout=self.timeout)

        run_time = time.time()
        p = self.run_proc(['s2p.sh', 'config.json'])
        self.wait_proc(p, timeout=self.timeout)
        self.cfg['info']['run_time'] = time.time() - run_time
        self.cfg.save()

        p = self.run_proc(['helper_convert_outputs.sh'])
        self.wait_proc(p, timeout=self.timeout)

        p = self.run_proc(['helper_archive.sh', 'config.json'])
        self.wait_proc(p, timeout=self.timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html", height=image(self.work_dir +
            'roi_ref_preview.png').size[1])
