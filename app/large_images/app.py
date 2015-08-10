"""
Display of large images
"""

from lib import base_app, build, http, image, config, thumbnail
from lib.misc import app_expose, ctime
from lib.base_app import init_app, AppPool
import cherrypy
from cherrypy import TimeoutError
import os.path
import shutil
import time
import numpy as np
import json
import ast
import subprocess

import utils

class app(base_app):
    """
    Display of large images
    """

    title = "Display of satellite images"
    xlink_article = 'http://www.ipol.im'
    input_tot_max_weight = 10000000

    is_test = True       # switch to False for deployment


    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)


    def build(self):
        """
        program build/update
        """
        # link to pleiades data
        if not os.path.lexists(os.path.join(self.input_dir, 'data')):
            os.symlink(os.path.join(os.path.expanduser("~"), 's2p_demo_data'),
                os.path.join(self.input_dir, 'data'))
        return

    @cherrypy.expose
    def index(self):
        """
        demo presentation and input menu
        """
        # read the input index as a dict
        input_dict = config.file_dict(self.input_dir)
        tn_size = int(cherrypy.config.get('input.thumbnail.size', '192'))
        # TODO: build via list-comprehension
        for (input_id, input_info) in input_dict.items():
            # convert the files to a list of file names
            # by splitting at blank characters
            # and generate thumbnails and thumbnail urls
            fnames = input_info['prv'].split()
            # generate thumbnails even for files in subdirectories of input
            input_dict[input_id]['tn_url'] = [self.input_url +'/'+ os.path.dirname(f) + '/' +
                        os.path.basename(thumbnail(self.input_dir + f, (tn_size, tn_size)))
                        for f in fnames]
            input_dict[input_id]['url'] = [self.input_url + os.path.basename(f)
                                       for f in fnames]

        return self.tmpl_out("input.html", inputd=input_dict)

    @cherrypy.expose
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

        # save paths to the tiff images
        # either one of the two keys dzi8 or dzi16 must exist
        input_dict = config.file_dict(self2.input_dir)
        self2.cfg['param']['tif_paths'] = input_dict[input_id]['tif'].split()
        self2.cfg['param']['nb_images'] = len(input_dict[input_id]['tif'].split())
        if input_dict[input_id].has_key('dzi8'):
            self2.cfg['param']['dzi_paths'] = input_dict[input_id]['dzi8'].split()
        else:
            self2.cfg['param']['dzi_paths'] = input_dict[input_id]['dzi16'].split()
        self2.cfg.save()

        # jump to the display page
        return self2.params(key=self2.key)


    @init_app
    def params(self, **kwargs):
        """
        Render the display page
        """
        dzi_paths = ast.literal_eval(self.cfg['param']['dzi_paths'])
        return self.tmpl_out("display.html", list_of_paths_to_dzi_files=dzi_paths)


    @cherrypy.expose
    @init_app
    def wait(self, x, y, w, h, i, crop_whole_sequence=False, **kwargs):
        """
        """
        # convert strings to ints
        x, y, w, h, i = map(int, [x, y, w, h, i])

        # save params
        self.cfg['param']['x'] = x
        self.cfg['param']['y'] = y
        self.cfg['param']['w'] = w
        self.cfg['param']['h'] = h
        self.cfg['param']['img_index'] = i
        self.cfg['param']['crop_whole_sequence'] = crop_whole_sequence
        self.cfg.save()

        # call run method through http
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")


    @cherrypy.expose
    @init_app
    def run(self, **kwargs):
        """
        """
        # read the params
        x = self.cfg['param']['x']
        y = self.cfg['param']['y']
        w = self.cfg['param']['w']
        h = self.cfg['param']['h']
        i = self.cfg['param']['img_index']
        crop_whole_sequence = self.cfg['param']['crop_whole_sequence']
        n = self.cfg['param']['nb_images']

        # run the algorithm
        try:
            run_time = time.time()
            self.run_algo(x, y, w, h, i, crop_whole_sequence)
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')
        http.redir_303(self.base_url + 'result?key=%s' % self.key)

        # archive
        if True:
            ar = self.make_archive()
            ar.add_info({"x": x, "y": y, "w": w, "h": h, "img_index": i,
                         "crop_whole_sequence": crop_whole_sequence})
            ar.add_file("crop_%02d.png" % i, info="selected crop (8 bits)")
            ar.add_file("crop_%02d.tif" % i, info="selected crop (16 bits)")
            if crop_whole_sequence:
                for k in xrange(1, n+1):
                    if k != i:
                        ar.add_file("crop_%02d.png" % k, info="corresponding crop (8 bits)")
                        ar.add_file("crop_%02d.tif" % k, info="corresponding crop (16 bits)")
            ar.save()

        return


    def run_algo(self, x, y, w, h, i, crop_whole_sequence):
        """
        """
        tif_paths = ast.literal_eval(self.cfg['param']['tif_paths'])
        if crop_whole_sequence:
            for k in xrange(1, len(tif_paths)+1):
                utils.crop(os.path.join(self.input_dir, tif_paths[k-1]),
                        os.path.join(self.work_dir, 'crop_%02d.tif' % k), x, y,
                        w, h)
                utils.qauto(os.path.join(self.work_dir, 'crop_%02d.tif' % k),
                        os.path.join(self.work_dir, 'crop_%02d.png' % k))
        else:
            utils.crop(os.path.join(self.input_dir, tif_paths[i-1]),
                    os.path.join(self.work_dir, 'crop_%02d.tif' % i), x, y, w, h)
            utils.qauto(os.path.join(self.work_dir, 'crop_%02d.tif' % i),
                    os.path.join(self.work_dir, 'crop_%02d.png' % i))

        return


    @cherrypy.expose
    @init_app
    def result(self):
        """
        """
        img_height = self.cfg['param']['h']
        whole_seq = self.cfg['param']['crop_whole_sequence']
        nb_img = len(ast.literal_eval(self.cfg['param']['tif_paths'])) if whole_seq else 1
        img_index = self.cfg['param']['img_index']
        return self.tmpl_out("result.html", height=img_height, n=nb_img,
                             img_index=img_index)


    @cherrypy.expose
    @init_app
    def browser_error(self, **kwargs):
        return self.tmpl_out('browser-error.html')
