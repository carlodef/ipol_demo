from lib import base_app
from lib.base_app import init_app
import cherrypy
import os.path

class app(base_app):

	title = "Hello World !"
	is_listed = False

	def __init__(self):
		base_dir = os.path.dirname(os.path.abspath(__file__))
		base_app.__init__(self, base_dir)

	@cherrypy.expose
	@init_app
	def index(self):
		nb = 3
		return self.tmpl_out("index.html", thing=nb)

	@cherrypy.expose
	@init_app
	def thing(self, number=""):
		print("I got this number = %s\n" % number)
		return self.tmpl_out("result.html", res=number)
