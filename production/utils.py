import sys
import os
import configparser

cfgpath = [os.path.join(os.path.dirname(sys.modules[__name__].__file__), '..', 'site.cfg')]
'Path list to search for configuration files.'


def get_path(name):
    '''Get path name info from site.cfg file in root directory.

    If a path does not exist, it will be created.
    '''
    conf = configparser.ConfigParser()
    cfgfile = conf.read(cfgpath)
    if cfgfile:
        print("Reading config file with path definitions: {}".format(cfgfile))
    else:
        raise Exception("No config file with path specifications found. File must be called 'site.py' and be located in one of the following directories: {}".format(cfgpath))
    path = conf.get("Path", name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path
