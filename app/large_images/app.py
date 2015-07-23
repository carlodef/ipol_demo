"""
Display of large images
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
import json
import ast
import subprocess

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
    @init_app
    def input_select(self, **kwargs):
        """
        use the selected available input images
        """
        self.init_cfg()

        # get the dataset id
        # kwargs contains input_id.x and input_id.y
        input_id = kwargs.keys()[0].split('.')[0]
        assert input_id == kwargs.keys()[1].split('.')[0]

#        # create symlinks to the full images and rpc files. There must be the
#        # same number of image files and rpc files. The number of previews
#        # doesn't matter.
#        img_files = input_dict[input_id]['img'].split()
#        img_files_abs = [os.path.join(self.input_dir, f) for f in img_files]
#        for i in range(len(img_files)):
#            os.symlink(img_files_abs[i], os.path.join(self.work_dir,
#                'img_%02d.tif' % (i+1)))
#
#        # if it's an xs dataset, create a link to the clr reference image
#        if 'clr' in input_dict[input_id]:
#            clr_files = input_dict[input_id]['clr'].split()
#            clr_files_abs = [os.path.join(self.input_dir, f) for f in clr_files]
#            os.symlink(img_files_abs[0], os.path.join(self.work_dir, 'img_01_clr.tif'))

        # save paths to the tiff images
        input_dict = config.file_dict(self.input_dir)
        self.cfg['param']['tif_paths'] = input_dict[input_id]['tif'].split()
        self.cfg['param']['dzi_paths'] = input_dict[input_id]['dzi16'].split()
        self.cfg.save()

        # jump to the display page
        return self.display(key=self.key)


    @init_app
    def display(self):
        """
        Render the display page 
        """
        dzi_paths = self.cfg['param']['dzi_paths']
        return self.tmpl_out("display.html", list_of_paths_to_dzi_files=dzi_paths)


    @cherrypy.expose
    @init_app
    def crop(self, x, y, w, h):
        """
        """
        tif_paths = ast.literal_eval(self.cfg['param']['tif_paths'])
        p = subprocess.Popen(['/usr/bin/gdal_translate', '-srcwin', str(x),
            str(y), str(w), str(h), os.path.join(self.input_dir, tif_paths[0]),
            os.path.join(self.work_dir, 'crop_1.tif')])
        return self.tmpl_out("result.html", height=h)

