from lib import base_app
from lib.base_app import init_app
from lib.misc import app_expose
import cherrypy
import os.path

class app(base_app):

    title = "Catalogue of Pleiades images"
    is_listed = False
    xlink_article = 'www.ipol.im'

    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_app.__init__(self, base_dir)

        # select the base_app steps to expose
        app_expose(base_app.index)

    @cherrypy.expose
    @init_app
    def thing(self, number=""):
        print("I got this number = %s\n" % number)
        return self.tmpl_out("result.html", res=number)
