#-------------------------------------------------------------------------------
# Point alignment detection demo
# by jose lezama, rafael grompone von gioi
# October 23, 2013
#-------------------------------------------------------------------------------

from lib import base_app, http, image
from lib.misc import app_expose, ctime
from lib.base_app import init_app
import cherrypy
from cherrypy import TimeoutError
import os.path
import json
import subprocess
import time

# for custom input_select:
from lib.base_app import config
import shutil

#-------------------------------------------------------------------------------
# Demo main class
#-------------------------------------------------------------------------------
class app(base_app):
    # IPOL demo system configuration
    title = 'Pushbroom camera attitude estimation'
    xlink_article = 'a.pdf'

    # Global variables for this demo
    sizeX = 512
    sizeY = 512

    #---------------------------------------------------------------------------
    # set up application
    #---------------------------------------------------------------------------
    def __init__(self):
        # setup the parent class
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        # index() and input_xxx() are generic
        base_app.index.im_func.exposed = True
        base_app.input_select.im_func.exposed = True
        # input_upload() is modified from the template
        base_app.input_upload.im_func.exposed = True
        # params() is modified from the template
        base_app.params.im_func.exposed = True
        # result() is modified from the template
        base_app.result.im_func.exposed = True

    # --------------------------------------------------------------------------
    # INPUT STEP
    # --------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def index(self, **kwargs):
        """
        use the selected available input images
        """
        self.new_key()
        self.init_cfg()

        try:
            prev_points = kwargs['zzblank.prev_points']
            prev_xs = []
            prev_ys = []
            for x, y in json.loads(prev_points):
                prev_xs.append(x)
                prev_ys.append(y)
        except:
            prev_xs = None
            prev_ys = None

        return self.params(key=self.key, prev_xs=prev_xs, prev_ys=prev_ys)

    #---------------------------------------------------------------------------
    # generate point selection page
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def params(self, newrun=False, msg=None, prev_xs=None, prev_ys=None):

        # initilize parameters
        self.cfg['param'] = {'img_width'  : self.sizeX,
                             'img_height' : self.sizeY,
                             'points'     : json.dumps( [] )}
        self.cfg.save()

        # generate dots image
        self.draw_points( self.cfg['param'] )

        # return the parameters page
        if newrun:
            self.clone_input()

        return self.tmpl_out('params.html',prev_xs=prev_xs,prev_ys=prev_ys)

    #---------------------------------------------------------------------------
    # draw points
    #---------------------------------------------------------------------------
    def draw_points(self, param):
        points = json.loads( param['points'] )
        width  = param['img_width']
        height = param['img_height']

        gifparam = 'GIF:' + self.work_dir + 'foreground.gif'
        ss = str(width) + 'x' + str(height)

        ptargs = []
        ptrad = 3
        ptcolor = '#FF0000'

        if len(points) > 0 :
            ptargs =  ['-stroke', ptcolor]
            ptargs += ['-strokewidth', '1.5', '-fill', ptcolor]
            ptargs += ['-draw', ' '.join(['circle %(x)i,%(y)i %(x)i,%(y_r)i'
                                          % {'x' : int(x*width),
                                             'y' : int(y*height),
                                             'y_r' : int(y*height) - ptrad}
                                            for (x,y) in points])]
        cmdrun = ['convert', '-quality', '100', '+antialias',
                  '-size', ss, 'xc:transparent'] + ptargs + [gifparam]
        subprocess.Popen( cmdrun ).wait()

    #---------------------------------------------------------------------------
    # input handling and run redirection
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def wait(self, **kwargs):
        kwargs = kwargs
        print kwargs
        try:
            points_x = kwargs['points_x'].split(',')
            points_y = kwargs['points_y'].split(',')
            print points_x
        except:
            points_x = self.cfg['param']['points_x'].split(',')
            points_y = self.cfg['param']['points_y'].split(',')

        try:
            self.cfg['meta']['original'] = kwargs['original']
            self.cfg.save()
        except:
            pass

        # convert strings to floats
        points_x = map(float, points_x)
        points_y = map(float, points_y)
        points_xy = zip(points_x, points_y)

        # write points coordinates to json file
        f = open(os.path.join(self.work_dir, 'params.json'), 'w')
        json.dump({'points': zip(points_x, points_y)}, f)
        f.close()
        
#        # write to text file
#        points = self.work_dir + "points.txt"
#        of = file(points, 'w')
#        of.writelines('%g %g\n' % (x, y) for (x, y) in points_xy)
#        of.close()

        # generate dots image
#        self.cfg['param']['points'] = json.dumps(points_xy)
#        self.cfg.save()
#        self.draw_points( self.cfg['param'] )

        http.refresh(self.base_url + 'run?key=%s' % self.key)
        return self.tmpl_out("wait.html")

    #---------------------------------------------------------------------------
    # run the algorithm
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def run(self, **kwargs):
        print "MYLOG, in beggining of run, key is %s" % self.key
        key=self.key

        kwargs=kwargs

        try:
            run_time = time.time()
            self.run_algo()
            self.cfg['info']['run_time'] = time.time() - run_time
            self.cfg.save()
        except TimeoutError:
            return self.error(errcode='timeout')
        except RuntimeError:
            return self.error(errcode='runtime')

#        # Archive
#        if self.cfg['meta']['original']:
#            ar = self.make_archive()
#            ar.add_file('points.txt', info='input points')
#            ar.add_file('points.eps', info='input points EPS')
#            ar.add_file('points.png', info='input points PNG')
#            ar.add_file('output.txt', info='output')
#            ar.add_file('output.eps', info='output EPS')
#            ar.add_file('output.png', info='output PNG')
#            ar.add_file('output2.eps', info='output EPS')
#            ar.add_file('output2.png', info='output PNG')
#            #ar.add_info({"points" : self.cfg['param']['points']})
#            ar.save()

        return self.result(key=self.key)

    #---------------------------------------------------------------------------
    # core algorithm runner
    # it could also be called by a batch processor, this one needs no parameter
    #---------------------------------------------------------------------------
    def run_algo(self):
        stdout = open(os.path.join(self.work_dir, 'stdout.txt'), 'w')
        p = self.run_proc(['run_single_image_problem.py', 'params.json'],
                          stdout=stdout)
        self.wait_proc(p)
        stdout.close()
        return

    #---------------------------------------------------------------------------
    # display the algorithm result
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def result(self, public=None):
        f = open(os.path.join(self.work_dir, 'params.json'), 'r')
        points = json.load(f)['points']
        f.close()

        return self.tmpl_out('result.html',
                             with_png=os.path.isfile(self.work_dir
                                                     + 'output.png'),
                             height=self.sizeX,
                             prev_points=points)

    #---------------------------------------------------------------------------
    # browser error
    #---------------------------------------------------------------------------
    @cherrypy.expose
    @init_app
    def browser_error(self, **kwargs):
        return self.tmpl_out('browser-error.html')

#-------------------------------------------------------------------------------
