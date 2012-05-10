from lib import base_app
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

    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

    
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
        for i in range(len(fnames)):
            shutil.copy(self.input_dir + fnames[i],
                        self.work_dir + 'input_%i' % i)
        msg = self.process_input()
        self.log("input selected : %s" % input_id)
        self.cfg['meta']['original'] = False
        self.cfg['meta']['input_id'] = input_id
        self.cfg.save()
        
        # jump to the crop page
        return self.crop(key=self.key)

    @cherrypy.expose
    def input_upload(self, **kwargs):
        """
        use the uploaded input images
        """
        self.new_key()
        self.init_cfg()
        for i in range(self.input_nb):
            file_up = kwargs['file_%i' % i]
            file_save = file(self.work_dir + 'input_%i' % i, 'wb')
            if '' == file_up.filename:
                # missing file
                raise cherrypy.HTTPError(400, # Bad Request
                                         "Missing input file")
            size = 0
            while True:
                # TODO larger data size
                data = file_up.file.read(128)
                if not data:
                    break
                size += len(data)
                if size > self.input_max_weight:
                    # file too heavy
                    raise cherrypy.HTTPError(400, # Bad Request
                                             "File too large, " + 
                                             "resize or use better compression")
                file_save.write(data)
            file_save.close()
        msg = self.process_input()
        self.log("input uploaded")
        self.cfg['meta']['original'] = True
        self.cfg.save()
        # jump to the crop page
        return self.crop(key=self.key)


    @cherrypy.expose
    @init_app
    def crop(self, done=None, x=None, y=None):
        """
        select a rectangle in the image
        """
        if done:
            # The crop is done, go to the results page
            sizeY = image(self.work_dir + 'out_0.png').size[1]
            return self.tmpl_out("results.html", sizeY=sizeY)
        
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
                plot_cross(self.work_dir + 'input_0.png', x, y, \
                           self.work_dir + 'input_0_corner.png')
                
                # change the page
                return self.tmpl_out("crop.html", corners=1)
            
            # Case 2 : 1 corner stored, the second has been clicked
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
                           self.work_dir + 'out_0.png')
               
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
                plot_rectangle(self.work_dir + 'input_1.png', x, y2, x3, y3, \
                               self.work_dir + 'input_1_selection.png')
                
                # crop from the first input image
                crop_image(self.work_dir + 'input_1.png', x, y2, x3, y3, \
                           self.work_dir + 'out_1.png')
                
                return self.tmpl_out("crop.html", corners=3)
        return
