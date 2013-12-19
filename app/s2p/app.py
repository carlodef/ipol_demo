"""
demo example for the X->aX+b transform
"""

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil

class app(base_app):
    """ template demo app """
    
    title = "f(x)=ax+b"
    xlink_article = 'http://www.ipol.im/'

    input_nb = 1 # number of input images
    input_max_pixels = 500000 # max size (in pixels) of an input image
    input_max_weight = 1 * 1024 * 1024 # max size (in bytes) of an input file
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
#        app_expose(base_app.index)
        app_expose(base_app.input_select)
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
        # store common file path in variables
        tgz_file = self.dl_dir + "io_png.tar.gz"
        prog_file = self.bin_dir + "axpb"
        log_file = self.base_dir + "build.log"
        # get the latest source archive
        build.download("http://tools.ipol.im/wiki/editor/demo/"
                       + "io_png.tar.gz", tgz_file)
        # test if the dest file is missing, or too old
        if (os.path.isfile(prog_file)
            and ctime(tgz_file) < ctime(prog_file)):
            cherrypy.log("not rebuild needed",
                         context='BUILD', traceback=False)
        else:
            # extract the archive
            build.extract(tgz_file, self.src_dir)
            # build the program
            build.run("make -j4 -C %s %s" % (self.src_dir + "io_png",
                                             os.path.join("example", "axpb")),
                      stdout=log_file)
            # save into bin dir
            if os.path.isdir(self.bin_dir):
                shutil.rmtree(self.bin_dir)
            os.mkdir(self.bin_dir)
            shutil.copy(self.src_dir + os.path.join("io_png", "example",
                                                    "axpb"), prog_file)
            # cleanup the source dir
            shutil.rmtree(self.src_dir)
        return

    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        params handling and run redirection
        """
        # save the parameters in self.cfg['param']
        # TODO: use dataset id
        self.cfg['param']['input_id'] = self.cfg['meta']['input_id']
        self.cfg['param']['out_dir'] = 's2p_results'
        self.cfg['param']['images'] = [
          { "img" : "pleiades_data/images/toulouse/im02.tif",
            "rpc" : "pleiades_data/rpc/toulouse/rpc02.xml",
            "clr" : "pleiades_data/images/toulouse/im02_color.tif" },
          { "img" : "pleiades_data/images/toulouse/im01.tif",
            "rpc" : "pleiades_data/rpc/toulouse/rpc01.xml" },
          { "img" : "pleiades_data/images/toulouse/im03.tif",
            "rpc" : "pleiades_data/rpc/toulouse/rpc03.xml" }
          ]
        self.cfg['param']['roi'] = {}
        self.cfg['param']['roi']['x'] = int(kwargs['x'])
        self.cfg['param']['roi']['y'] = int(kwargs['y'])
        self.cfg['param']['roi']['w'] = int(kwargs['roi_size'])
        self.cfg['param']['roi']['h'] = int(kwargs['roi_size'])
        self.cfg['param']["matching_algorithm"] = "hirschmuller08"
        self.cfg['param']['subsampling_factor'] = int(kwargs['zoom'])
        self.cfg['param']["subsampling_factor_registration"] = 1
        self.cfg['param']["sift_match_thresh"] = 0.4
        self.cfg['param']["disp_range_extra_margin"] = 0.2
        self.cfg['param']["n_gcp_per_axis"] = 5
        self.cfg['param']["epipolar_thresh"] = 0.5
        self.cfg['param']["use_pleiades_unsharpening"] = True
        self.cfg['param']["debug"] = False
        self.cfg['param']["preview_coordinate_system"] = True

        self.cfg['meta']["orig"] = True
        self.cfg.save()

        # write the parameters in a json file
        import json
        fp = open(self.work_dir+'config.json', 'w')
        json.dump(self.cfg['param'], fp, indent=4)
        fp.close()

        # save and validate the parameters
#        try:
#            self.cfg['param'] = {'a' : float(a),
#                                 'b' : float(b)}
#        except ValueError:
#            return self.error(errcode='badparams',
#                              errmsg="The parameters must be numeric.")

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    @cherrypy.expose
    @init_app
    def run(self):
        """
        algo execution
        """
        os.symlink(self.input_dir+'/data', self.work_dir+'/pleiades_data')

        # run the algorithm
        try:
            self.run_algo()
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
            ar.add_file("input_0.png", "input.png", info="input")
            ar.add_file("s2p_results/dem_fusion_preview.png", info="output")
            ar.add_file("s2p_results/roi_color_ref_preview.png", info="output")
            ar.add_file("s2p_results/roi_ref_preview.png", info="output")
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

        p = self.run_proc(['s2p.sh', 'config.json'])
        self.wait_proc(p, timeout=self.timeout)

        p = self.run_proc(['helper_convert_outputs.sh'])
        self.wait_proc(p, timeout=self.timeout)
        return

    @cherrypy.expose
    @init_app
    def result(self):
        """
        display the algo results
        """
        return self.tmpl_out("result.html",
                             height=image(self.work_dir
                                          + 's2p_results/dem_fusion_preview.png').size[1])
