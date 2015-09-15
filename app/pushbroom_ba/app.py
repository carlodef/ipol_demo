#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0103

"""
Attitude refinement for orbiting pushbroom cameras - IPOL demo
by Carlo de Franchis, Gabriele Facciolo, Enric Meinhardt
May 2015

The javascript tool to plot points was copied from
Point alignment detection demo
by Jose Lezama, Rafael Grompone von Gioi
"""

import cherrypy
import os.path
import json
import time
import pylab

from lib import base_app, http
from lib.base_app import init_app, AppPool

class app(base_app):
    """
    App object for the attitude refinement IPOL demo.
    """

    # IPOL demo system configuration
    title = 'Attitude estimation for orbiting pushbroom cameras'
    #xlink_article = 'http://boucantrin.ovh.hw.ipol.im/~carlo/2015_ipol_pushbroom_camera_estimation.pdf'
    xlink_article = 'boucantrin.ovh.hw.ipol.im/~carlo/attitude_refinement.pdf'


    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)


    def build(self):
        """
        Update local copy of pushbroom_ba source from its git repository.
        """
        if not os.path.isdir(self.bin_dir):
            # bin directory not found, doing a git clone
            cmd = ("git clone -b ipol --depth 1"
                   " git@github.com:carlodef/pushbroom_calibration.git %s" % self.bin_dir)
            os.system(cmd)
        else:
            # bin directory found, doing a git pull
            os.system("cd %s && git pull && cd -" % self.bin_dir)

        return


    @cherrypy.expose
    def index(self, **kwargs):
        """
        Handle the key generation and redirect to the params method.
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

        # do my stuff
        try:
            prev_points = json.loads(kwargs['zzblank.prev_points'])
        except BaseException:
            prev_points = None

        return self2.params(key=self2.key, prev_points=prev_points)


    @cherrypy.expose
    @init_app
    def params(self, newrun=False, prev_points=None):
        """
        Generate point selection page.
        """
        # initialize parameters
        self.cfg['param'] = {'points': json.dumps([]), 'has_already_run': False}
        self.cfg.save()

        # return the parameters page
        if newrun:
            self.clone_input()

        return self.tmpl_out('paramresult.html', prev_points=prev_points)

    def draw_points(self, pts_x, pts_y):
        """
        Draw user-selected points in a png file.
        """
        pylab.clf()
        pylab.plot(pts_x, [1-y for y in pts_y], marker='o', color='r', ls='')
        pylab.xlim(-.05, 1.05)
        pylab.ylim(-.05, 1.05)
        pylab.axis('off')
        pylab.savefig(os.path.join(self.work_dir, 'points.png'),
                      bbox_inches='tight')


    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        """
        Input handling and run redirection.
        """
        # read points coordinates
        points_x = kwargs['points_x'] if kwargs.has_key('points_x') \
                                      else self.cfg['param']['points_x']
        points_y = kwargs['points_y'] if kwargs.has_key('points_y') \
                                      else self.cfg['param']['points_y']

        # convert strings to floats
        points_x = [float(x) for x in points_x.split(',')]
        points_y = [float(x) for x in points_y.split(',')]

        # save the displayed points coordinates
        self.cfg['param']['points'] = [[x, y] for x, y in zip(points_x,
                                                              points_y)]
        self.cfg['param']['npts'] = len(self.cfg['param']['points'])
        self.cfg['param']['img_width'] = 512
        self.cfg['param']['img_height'] = 512
        self.draw_points(points_x, points_y)

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

        # perturbation
        self.cfg['param']['perturbation_amplitude'] = kwargs['perturbation_amplitude']
        algo_params['perturbation_amplitude'] = 1e-6 * float(kwargs['perturbation_amplitude'])
        self.cfg['param']['perturbation_degree'] = kwargs['perturbation_degree']
        algo_params['perturbation_degree'] = int(kwargs['perturbation_degree'])

        # normalized points coordinates
        alts = [0] * len(points_x)
        #alts = [0 for a in points_x]
        algo_params['points'] = zip(points_y, points_x, alts)
        algo_params['normalized_points'] = True

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


    @cherrypy.expose
    @init_app
    def run(self):
        """
        Run the algorithm.
        """
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
        ar.add_file('attitude_residuals.png', info='attitude errors')
        ar.add_file('attitude_estimated_vs_measured_vs_truth.png',
                    info='attitudes (estimated, measured and true)')
        ar.add_info({"nb points" : int(self.cfg['param']['npts'])})
        ar.add_info({"sigma" : [self.cfg['param']['sigma_pixels'],
                                self.cfg['param']['sigma_meters']]})
        ar.save()

        http.redir_303(self.base_url + 'result?key=%s' % self.key)
        return self.tmpl_out("run.html")


    def run_algo(self, params=None):
        """
        Core algorithm runner. It could also be called by a batch processor.
        """
        stdout = open(os.path.join(self.work_dir, 'stdout.txt'), 'w')
        stderr = open(os.path.join(self.work_dir, 'stderr.txt'), 'w')
        p = self.run_proc(['run_single_image_problem.py', 'params.json',
                           'gcp.txt'], stdout=stdout, stderr=stderr)
        self.wait_proc(p)
        stdout.close()
        stderr.close()
        return


    @cherrypy.expose
    @init_app
    def result(self, public=None):
        """
        Display the algorithm result
        """

        self.cfg['param']['has_already_run'] = True
        self.cfg.save()

        return self.tmpl_out('paramresult.html',
                             prev_points=self.cfg['param']['points'])


    @cherrypy.expose
    @init_app
    def browser_error(self):
        """
        Browser error
        """
        return self.tmpl_out('browser-error.html')
