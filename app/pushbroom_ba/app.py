#-------------------------------------------------------------------------------
# Attitude estimation for orbiting pushbroom cameras - IPOL demo
# by Carlo de Franchis, Gabriele Facciolo, Enric Meinhardt
# May 2015
#
# The javascript tool to plot points was copied from
# Point alignment detection demo
# by jose lezama, rafael grompone von gioi
# October 23, 2013
#-------------------------------------------------------------------------------
import subprocess
import cherrypy
import os.path
import json
import time
import pylab
import cherrypy.lib.profiler


from lib import base_app, http
from lib.base_app import init_app

#-------------------------------------------------------------------------------
# Demo main class
#-------------------------------------------------------------------------------
class app(base_app):
    # IPOL demo system configuration
    title = 'Attitude estimation for orbiting pushbroom cameras'
    xlink_article = 'http://boucantrin.ovh.hw.ipol.im/~carlo/2015_ipol_pushbroom_camera_estimation.pdf'

    p = cherrypy.lib.profiler.Profiler("/tmp/kkprof")

    #---------------------------------------------------------------------------
    # set up application
    #---------------------------------------------------------------------------
    def __init__(self):
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)


    def build(self):
        """
        update local copy of pushbroom_ba source from its git repository
        """
        if not os.path.isdir(self.bin_dir):
            print 'bin directory not found, doing a git clone'
            cmd = ("git clone -b ipol --single-branch --depth 1"
                   " git@github.com:carlodef/pushbroom_calibration.git %s" % self.bin_dir)
            os.system(cmd)
        else:
            print 'bin directory found, doing a git pull'
            os.system("cd %s && pwd && git pull && cd -" % self.bin_dir)

        return

    # --------------------------------------------------------------------------
    # INPUT STEP
    # --------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def index(self, **kwargs):
        """
        use the selected available input images
        """
        self.init_cfg()

        try:
            prev_points = json.loads(kwargs['zzblank.prev_points'])
        except:
            prev_points = None

        return self.params(key=self.key, prev_points=prev_points)

    #---------------------------------------------------------------------------
    # generate point selection page
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, prev_points=None):

        # initialize parameters
        self.cfg['param'] = {'points': json.dumps([]), 'has_already_run': False}
        self.cfg.save()

        # return the parameters page
        if newrun:
            self.clone_input()

        return self.tmpl_out('paramresult.html', prev_points=prev_points)

    #---------------------------------------------------------------------------
    # draw points
    #---------------------------------------------------------------------------
    def draw_points(self, pts_x, pts_y, width, height):
        pylab.plot(pts_x, pts_y, marker='o', color='r', ls='')
        pylab.savefig(os.path.join(self.work_dir, 'points.png'),
                      bbox_inches='tight')


    #---------------------------------------------------------------------------
    # input handling and run redirection
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        self.p.run(self._wait, **kwargs)

    @init_app
    def _wait(self, **kwargs):

        # read points coordinates
        points_x = kwargs['points_x'] if kwargs.has_key('points_x') else self.cfg['param']['points_x']
        points_y = kwargs['points_y'] if kwargs.has_key('points_y') else self.cfg['param']['points_y']

        # convert strings to floats
        points_x = [float(x) for x in points_x.split(',')]
        points_y = [float(x) for x in points_y.split(',')]

        # save the displayed points coordinates
        self.cfg['param']['points'] = [[x, y] for x, y in zip(points_x,
                                                              points_y)]
        self.cfg['param']['npts'] = len(self.cfg['param']['points'])
        self.cfg['param']['img_width'] = 512
        self.cfg['param']['img_height'] = 512
        self.draw_points(points_x, points_y, 512, 512)

        # create a json file containing the parameters for the algo
        algo_params = {}

        # camera type
        self.cfg['param']['camera_type'] = kwargs['camera_type']
        self.cfg['param']['psi_x'] = kwargs['psi_x']
        self.cfg['param']['psi_y'] = kwargs['psi_y']
        algo_params['camera'] = {}
        algo_params['camera']['instrument'] = kwargs['camera_type']
        algo_params['camera']['orbit'] = kwargs['camera_type']
        algo_params['camera']['view'] = {}
        algo_params['camera']['view']['psi_x'] = float(kwargs['psi_x'])
        algo_params['camera']['view']['psi_y'] = float(kwargs['psi_y'])

        # points coordinates, rescaled to image dimensions
        rows = [40000 * float(a) for a in points_y]
        cols = [40000 * float(a) for a in points_x]
        alts = [0 for a in points_x]
        algo_params['points'] = zip(rows, cols, alts)

        # noise parameters
        self.cfg['param']['sigma_pixels'] = float(kwargs['sigma_pixels'])
        self.cfg['param']['sigma_meters'] = float(kwargs['sigma_meters'])
        algo_params['sigma'] = [self.cfg['param']['sigma_pixels'],
                                self.cfg['param']['sigma_meters']]

        # write to json file
        f = open(os.path.join(self.work_dir, 'params.json'), 'w')
        json.dump(algo_params, f)
        f.close()

        # meta info
        if kwargs.has_key('original'):
            self.cfg['meta']['original'] = kwargs['original']

        self.cfg.save()
        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    #---------------------------------------------------------------------------
    # run the algorithm
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def run(self, **kwargs):

        try:
            run_time = time.time()
            self.run_algo()
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except cherrypy.TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')

        # archive
        ar = self.make_archive()
        ar.add_file('params.json', info='input parameters and point coordinates')
        ar.add_file('gcp.txt', info='list of (row, col, alt, lon, lat)'
                                    ' correspondences actually used (ie after'
                                    ' noise addition) to estimate the attitudes')
        ar.add_file('stdout.txt', info='algo output')
        ar.add_file('points.png', info='input points')
        ar.add_info({"nb points" : int(self.cfg['param']['npts'])})
        ar.add_info({"sigma" : [self.cfg['param']['sigma_pixels'],
                                self.cfg['param']['sigma_meters']]})
        ar.save()

        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")

    #---------------------------------------------------------------------------
    # core algorithm runner
    # it could also be called by a batch processor, this one needs no parameter
    #---------------------------------------------------------------------------
    def run_algo(self):
        stdout = open(os.path.join(self.work_dir, 'stdout.txt'), 'w')
        p = self.run_proc(['run_single_image_problem.py', 'params.json',
                           'gcp.txt'], stdout=stdout)
        self.wait_proc(p)
        stdout.close()
        return

    #---------------------------------------------------------------------------
    # display the algorithm result
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def result(self):

        self.cfg['param']['has_already_run'] = True
        self.cfg.save()

        return self.tmpl_out('paramresult.html',
                             prev_points=self.cfg['param']['points'])

    #---------------------------------------------------------------------------
    # browser error
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def browser_error(self, **kwargs):
        return self.tmpl_out('browser-error.html')
