"""
empty IPOL demo web app
"""
# pylint: disable=C0103

#
# EMPTY APP
#

import hashlib
from datetime import datetime
from random import random

import os
import time
from subprocess import Popen

from cherrypy import TimeoutError
import cherrypy

class empty_app(object):
    """
    This app only contains configuration and tools, no actions.
    """
    # TODO : rewrite the url functions

    def __init__(self, base_dir):
        """
        app setup

        @param base_dir: the base directory for this demo, used to
        look for special subfolders (input, tmp, ...)
        """
        # the demo ID is the folder name
        self.base_dir = os.path.abspath(base_dir) + os.path.sep
        self.id = os.path.basename(base_dir)
        self.key = ''

        # create the missing subfolders
        for static_dir in [self.input_dir, self.tmp_dir]:
            if not os.path.isdir(static_dir):
                cherrypy.log("warning: missing static folder, "
                             "creating it : %s" % static_dir,
                             context='SETUP', traceback=False)
                os.mkdir(static_dir)
                
        # static folders
        # cherrypy.tools.staticdir is a decorator,
        # ie a function modifier
        self.input = cherrypy.tools.staticdir(dir=self.input_dir)\
            (lambda x : None)
        self.tmp = cherrypy.tools.staticdir(dir=self.tmp_dir)\
            (lambda x : None)

    def __getattr__(self, attr):
        """
        direct access to some image attributes
        """

        # subfolder patterns
        folder_pattern = {'input_dir' : 'input',
                          'dl_dir' : 'dl',
                          'src_dir' : 'src',
                          'bin_dir' : 'bin',
                          'tmp_dir' : 'tmp',
                          'work_dir' : os.path.join('tmp', self.key)}

        # subfolders
        if attr in folder_pattern:
            value = os.path.join(self.base_dir,
                                 folder_pattern[attr])
            value = os.path.abspath(value)+ os.path.sep
        # url
        elif attr == 'base_url':
            value = cherrypy.url(path="/")
        elif attr == 'input_url':
            value = cherrypy.url(path="/input/")
        elif attr == 'tmp_url':
            value = cherrypy.url(path="/tmp/")
        elif attr == 'work_url':
            value = cherrypy.url(path="/tmp/%s/" % self.key)
        # real attribute
        else:
            value = object.__getattribute__(self, attr)
        return value

    #
    # UPDATE
    #

    def build(self):
        """
        virtual function, to be overriden by subclasses
        """
        cherrypy.log("warning: no build method",
                     context='SETUP/%s' % self.id, traceback=False)

    #
    # KEY MANAGEMENT
    #

    def new_key(self):
        """
        create a key and its storage folder
        """
        keygen = hashlib.md5()
        seeds = [cherrypy.request.remote.ip,
                 # use port to improve discrimination
                 # for proxied or NAT clients 
                 cherrypy.request.remote.port, 
                 datetime.now(),
                 random()]
        for seed in seeds:
            keygen.update(str(seed))
        self.key = keygen.hexdigest()
        os.mkdir(self.work_dir)
        return

    def check_key(self):
        """
        verify a key exists, is safe and valid,
        and raise an error if it doesn't
        """
        
        if not (self.key
                and self.key.isalnum()
                and os.path.isdir(self.work_dir)
                and (self.tmp_dir == 
                     os.path.commonprefix([self.work_dir, self.tmp_dir]))):
            raise cherrypy.HTTPError(400, # Bad Request
                                     "The key is invalid")

    #
    # LOGS
    #

    def log(self, msg):
        """
        simplified log handler

        @param msg: the log message string
        """
        cherrypy.log(msg, context="DEMO/%s/%s" % (self.id, self.key),
                     traceback=False)
        return

    #
    # SUBPROCESS
    #

    def run_proc(self, args, stdin=None, stdout=None, stderr=None):
        """
        execute a sub-process from the 'tmp' folder
        """
        # update the environment
        newenv = os.environ.copy()
        # TODO clear the PATH, hard-rewrite the exec arg0
        # TODO use shell-string execution
        newenv.update({'PATH' : self.bin_dir})
        # run
        return Popen(args, stdin=stdin, stdout=stdout, stderr=stderr,
                     env=newenv, cwd=self.work_dir)

    def wait_proc(self, process, timeout=False):
        """
        wait for the end of a process execution with an optional timeout
        timeout: False (no timeout) or a numeric value (seconds)
        process: a process or a process list, tuple, ...
        """

        if not (cherrypy.config['server.environment'] == 'production'):
            # no timeout if just testing
            timeout = False
        if isinstance(process, Popen):
            # require a list
            process_list = [process]
        else:
            # duck typing, suppose we have an iterable
            process_list = process
        if not timeout:
            # timeout is False, None or 0
            # wait until everything is finished
            for p in process_list:
                p.wait()
        else:
            # http://stackoverflow.com/questions/1191374/
            # wainting for better : http://bugs.python.org/issue5673
            start_time = time.time()
            run_time = 0
            while True:
                if all([p.poll() is not None for p in process_list]):
                    # all processes have terminated
                    break
                run_time = time.time() - start_time
                if run_time > timeout:
                    for p in process_list:
                        try:
                            p.terminate()
                        except OSError:
                            # could not stop the process
                            # probably self-terminated
                            pass
                    raise TimeoutError
                time.sleep(0.1)
        if any([0 != p.returncode for p in process_list]):
            raise RuntimeError
        return
