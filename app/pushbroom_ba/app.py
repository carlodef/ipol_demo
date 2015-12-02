#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=C0103

"""
Attitude refinement for orbiting pushbroom cameras - IPOL demo
by Carlo de Franchis, Gabriele Facciolo, Enric Meinhardt
May 2015. Revised November 2015.

The javascript tool to plot points was copied from
Point alignment detection demo
by Jose Lezama, Rafael Grompone von Gioi
"""

import cherrypy
import os.path
import shutil
import glob
import json
import time
import sys

import matplotlib
matplotlib.use('Agg')
import pylab

from lib import base_app, http, build
from lib.base_app import init_app

class app(base_app):
    """
    App object for the attitude refinement IPOL demo.
    """

    # IPOL demo system configuration
    title = 'Attitude Refinement for Orbiting Pushbroom Cameras'
    xlink_article = 'http://www.ipol.im/pub/pre/146/preprint.pdf'
    xlink_src = 'http://www.ipol.im/pub/pre/146/src_pushbroom.tar.gz'


    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)


    def build(self):
        """
        Download and install the source code published in IPOL with the paper.
        """
        # copy the python src code of the paper in the bin directory
        tgz_file = os.path.join(self.dl_dir, 'src_pushbroom.tar.gz')
        build.download(self.xlink_src, tgz_file)
        build.extract(tgz_file, self.src_dir)
        if not os.path.isdir(self.bin_dir):
            os.mkdir(self.bin_dir)
        for f in os.listdir(os.path.join(self.src_dir, 'src_pushbroom')):
            ff = os.path.join(self.src_dir, 'src_pushbroom', f)
            if os.path.isfile(ff) and f.endswith('.py'):
                shutil.copy(ff, self.bin_dir)

        # check if the dependencies are met (cvxopt and numpy)
        site_packages_dir = os.path.join(self.base_dir, 'lib', 'python2.7', 'site-packages')
        sys.path.insert(0, site_packages_dir)
        eggs = glob.glob(os.path.join(site_packages_dir, '*.egg'))
        for egg in eggs:
            sys.path.insert(0, egg)
        try:
            import cvxopt
        except ImportError:
            self._build_pkg('cvxopt-1.1.7')
        try:
            import numpy
            if numpy.version.version < '1.9.0':
                raise ImportWarning('this code requires numpy version >= 1.9.0')
        except (ImportError, ImportWarning):
            self._build_pkg('numpy-1.9.2', opts='--fcompiler=gnu95')
        return


    def _build_pkg(self, pkg_name, opts=''):
        """
        Compile a 3rdparty package from the sources shipped with the IPOL paper.
        """
        third_party_dir = os.path.join(self.src_dir, 'src_pushbroom', '3rdparty')
        work_dir = os.path.join(third_party_dir, pkg_name, pkg_name)

        # build
        tgz_file = os.path.join(third_party_dir, '%s.tar.gz' % pkg_name)
        log_build = os.path.join(self.base_dir, 'build-%s.log' % pkg_name)
        build.extract(tgz_file, os.path.join(third_party_dir, pkg_name))
        build.run('python setup.py build %s' % opts, log_build, cwd=work_dir)

        # install
        log_install = os.path.join(self.base_dir, 'install-%s.log' % pkg_name)
        site_packages = os.path.join(self.base_dir, 'lib', 'python2.7', 'site-packages')
        if not os.path.isdir(site_packages):
            os.makedirs(site_packages)
        build.run('python setup.py install --prefix=%s' % self.base_dir, log_install,
                  cwd=work_dir, env={'PYTHONPATH': site_packages})


    @cherrypy.expose
    def index(self):
        """
        Redirect to the params method directly, as this demo as no input data.
        """
        return self.params()


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
        if kwargs.has_key('points_x'):
            points_x = kwargs['points_x']
        else:
            points_x = self.cfg['param']['points_x']
        if kwargs.has_key('points_y'):
            points_y = kwargs['points_y']
        else:
            points_y = self.cfg['param']['points_y']

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
        self.cfg['param']['gamma'] = kwargs['gamma']
        algo_params['camera'] = {}
        algo_params['camera']['instrument'] = kwargs['camera_type']
        algo_params['camera']['orbit'] = kwargs['camera_type']
        algo_params['camera']['view'] = {}
        algo_params['camera']['view']['psi_x'] = float(kwargs['psi_x'])
        algo_params['camera']['view']['psi_y'] = float(kwargs['psi_y'])
        algo_params['camera']['view']['gamma'] = float(kwargs['gamma'])

        # perturbation
        self.cfg['param']['perturbation_amplitude'] = kwargs['perturbation_amplitude']
        algo_params['perturbation_amplitude'] = 1e-6 * float(kwargs['perturbation_amplitude'])
        self.cfg['param']['perturbation_degree'] = kwargs['perturbation_degree']
        algo_params['perturbation_degree'] = int(kwargs['perturbation_degree'])

        # normalized points coordinates
        algo_params['points'] = zip(points_y, points_x)
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
        site_packages = os.path.join(self.base_dir, 'lib', 'python2.7',
                                     'site-packages')
        p = self.run_proc(['run_single_image_problem.py', 'params.json',
                           'gcp.txt'], stdout=stdout, stderr=stderr,
                          env={'PYTHONPATH': site_packages})
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
