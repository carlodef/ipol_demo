"""
config dictionary with file backend

This file can save integer, float, boolean and strings as options
"""
# designed based on http://code.activestate.com/recipes/576642/,
# (C) Raymond Hettinger, MIT licence

import json
import os
import shutil
import tempfile

class file_dict_json(dict):
    """
    handle a config file as a dictionary
    """
    def __init__(self, filename, flag='c', mode=None, *args, **kwargs):
        """
        create a dictionary from a config file

        @param filename: config file name or folder
        @param flag r=readonly, c=create, or n=new
        @param mode file permissions: None or octal triple like 0x666
        """
        dict.__init__(self)
        self.flag = flag
        self.mode = mode
        self.filename = filename
        if os.path.isdir(filename):
            self.filename = os.path.join(self.filename, "index.cfg")
        # if flag == 'n', don't read the file
        if flag != 'n' and os.path.isfile(self.filename):
            # the file must be readable
            infile = open(self.filename, 'rb')
            try:
                # update the dict with the file content
                self.load(infile)
            finally:
                infile.close()
        self.update(*args, **kwargs)

    def load(self, infile):
        """
        read a config file into the dictionary
        """
        infile.seek(0)
        try:
            cfg = json.load(infile)
        except Exception:
            raise ValueError('File not in recognized format')
        return self.update(cfg)

    def save(self):
        """
        alias to sync()
        """
        self.sync()

    def sync(self):
        """
        atomic sync to file
        """
        # readonly: do nothing
        if self.flag == 'r':
            return
        (fd, tempname) = tempfile.mkstemp()
        outfile = os.fdopen(fd, 'wb')
        try:
            json.dump(self, outfile, indent=4)
        except Exception:
            outfile.close()
            os.remove(tempname)
            raise
        outfile.close()
        if self.mode is not None:
            os.chmod(tempname, self.mode)
        shutil.move(tempname, self.filename)    # atomic commit


def cfg_open(filename, flag=None, mode=None):
    """
    open a config file as a dictionary
    """
    return file_dict_json(filename, flag, mode)


if __name__ == '__main__':

    os.chdir('/tmp')
    testcfg = cfg_open('test.cfg', 'n')
    testcfg['numeric'] = {'a':123, 'b':0, 'c':3.14159}
    testcfg['bool'] = {'ok' : True, 'ko' : False}
    testcfg['str'] = {'a' : "alpha", 'b' : "beta gamma delta"}
    testcfg.save()
    f = open('test.cfg', 'rb')
    print (f.read())
    f.close()
    testcfg = cfg_open('test.cfg')
    print testcfg
