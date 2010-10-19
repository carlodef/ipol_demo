"""
cwinterp ipol demo web app
"""
# pylint: disable=C0103

from lib import base_app
from lib import get_check_key, http_redirect_303
import cherrypy
from cherrypy import TimeoutError
from lib import image
import os.path
import time

class app(base_app):
    """ cwinterp app """

    title = "Contour Stencil Windowed Interpolation"
    description = "Edge-directed image interpolation" \
        + " based on total variation along curves. "

    input_nb = 1
    input_max_pixels = 480000 # max size (in pixels) of an input image
    input_max_weight = 3 * 1024 * 1024 # max size (in bytes) of an input file
    input_dtype = '3x8i' # input image expected data type
    input_ext = '.png' # input image expected extension (ie file format)
    is_test = True

    def __init__(self):
        """
        app setup
        """
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True


    # run() is defined here,
    # because the parameters validation depends on the algorithm
    @cherrypy.expose
    @get_check_key
    def run(self):
        """
        params handling and run redirection
        as a special case, we have no parameter to check and pass
        """
        http_redirect_303(self.url('result', {'key':self.key}))
        urld = {'next_step' : self.url('result'),
                'input' : [self.url('tmp', 'input_%i.png' % i)
                           for i in range(self.input_nb)]}
        return self.tmpl_out("run.html", urld=urld)

    # run_algo() is defined here,
    # because it is the actual algorithm execution, hence specific
    # run_algo() is called from result(),
    # with the parameters validated in run()
    def run_algo(self, stdout=None, timeout=False):
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """
        """
        the core algo runner
        could also be called by a batch processor
        this one needs no parameter
        """

        #check image dimensions (must be divisible by 4)
        img0 = image(self.path('tmp', 'input_0.png'))
        sizeX = img0.size[0]
        sizeY = img0.size[1]
        sizeXX = (sizeX/4)*4
        sizeYY = (sizeY/4)*4
        img0.crop((0, 0, sizeXX, sizeYY))       
        img0.save(self.path('tmp', 'input_1.png'))


        a = 4
        b = 0.35
        p = self.run_proc(['imcoarsen', str(a), str(b),
                           'input_1.png', 'coarsened.png'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc(p, timeout)

        p2 = self.run_proc(['cwinterp', 'coarsened.png', 'interpolated.png'],
                          stdout=stdout, stderr=stdout)
        p4 = self.run_proc(['cwinterp', '-s', 'coarsened.png',
                            'contourori.png'],
                           stdout=stdout, stderr=stdout)
        self.wait_proc(p2, timeout)

        p3 = self.run_proc(['imdiff', 'input_1.png', 'interpolated.png'],
                          stdout=stdout, stderr=stdout)
        self.wait_proc([p3, p4], timeout)

        img0 = image(self.path('tmp', 'input_1.png'))
        sizeX = img0.size[0]
        sizeY = img0.size[1]
        img1 = image(self.path('tmp', 'coarsened.png'))
        img1.resize((sizeX, sizeY), method="nearest")
        img1.save(self.path('tmp', 'coarsenedZ.png'))

        return

    @cherrypy.expose
    @get_check_key
    def result(self):
        """
        display the algo results
        SHOULD be defined in the derived classes, to check the parameters
        """
        # run the algorithm
        stdout = open(self.path('tmp', 'stdout.txt'), 'w')
        try:
            run_time = time.time()
            self.run_algo(stdout=stdout)
            run_time = time.time() - run_time
        except TimeoutError:
            return self.error(errcode='timeout') 
        except RuntimeError:
            return self.error(errcode='runtime')
        self.log("input processed")
        urld = {'new_run' : self.url('params'),
                'new_input' : self.url('index'),
                'input' : [self.url('tmp', 'input_1.png')],
                'output' : [self.url('tmp', 'coarsenedZ.png'),
                            self.url('tmp', 'interpolated.png'),
                            self.url('tmp', 'contourori.png')],
                }
        stdout = open(self.path('tmp', 'stdout.txt'), 'r')
        return self.tmpl_out("result.html", urld=urld, stdout=stdout.read())

