#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# file_utils.py: small function helper code for working with local file system
import os
import stat
import yaml
import fnmatch
import shutil
import tempfile

from xtlib import console
from xtlib import pc_utils

def has_wildcards(name):
    has_wild = ("*" in name) or ("?" in name)
    return has_wild

def get_first_dirnode(path):
    path = path.replace("\\", "/")
    parts = path.split("/")
    first = parts[0]
    rest = parts[1:]

    return first, rest
    
def get_xthome_dir():
    return get_home_dir() + "/.xt"

def get_home_dir():
    if pc_utils.is_windows():
        # running on windows
        home_dir = os.getenv('USERPROFILE') 
        home_dir = home_dir.replace("\\", "/")
    else:
        home_dir = os.getenv('HOME') 
    return home_dir 

def get_config_fn():
    return get_xthome_dir() + "/xt_config.yaml"

def get_dev_config_fn():
    return get_xthome_dir() + "/xt_dev_config.yaml"

def zap_file(fn):
    if os.path.exists(fn):
        try:
            os.remove(fn)
        except PermissionError:
            # make readonly file writable
            make_readwrite(fn)
            os.remove(fn)

def make_readonly(fn):
    os.chmod(fn, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

def make_readwrite(fn):
     os.chmod(fn, stat.S_IWRITE)

def zap_dir(dir):
    ''' this will delete all files recursively, including readonly files (unlike shutil.rmtree)
    '''
    if os.path.exists(dir):
        for name in os.listdir(dir):
            path = os.path.join(dir, name)

            if os.path.isfile(path):
                zap_file(path)
            else:
                zap_dir(path)

        # remove the root dir for our call
        os.rmdir(dir)

def ensure_dir_exists(dir=None, file=None):
    if file:
        dir = os.path.dirname(file)
    
    if dir and not os.path.exists(dir):
        os.makedirs(dir)

def ensure_dir_deleted(dir):
    if os.path.exists(dir):
        zap_dir(dir)

def ensure_dir_clean(dir):
    if os.path.exists(dir):
        zap_dir(dir)
    os.makedirs(dir)

def read_text_file(fn, as_lines=False):
    fn = os.path.expanduser(fn)

    with open(fn, "r") as tfile:
        text = tfile.read()

    if as_lines:
        # remove any rouge CR chars
        text = text.replace("\r", "")
        text = text.split("\n")
    return text

def write_text_file(fn, text, newline=None):
    fn = os.path.expanduser(fn)
    ensure_dir_exists(file=fn)
    
    with open(fn, "w", newline=newline) as tfile:
        tfile.write(text)

def split_dirname_basename(path):
    dir_name = os.path.dirname(path)
    base_name = os.path.basename(path)
    return dir_name, base_name

def split_wc_path(path):
    if "*" in path or "?" in path:
        dir_name = os.path.dirname(path)
        wc_target = os.path.basename(path)
    else:
        dir_name = path
        wc_target = None

    return dir_name, wc_target

def glob(wildpath, return_path=True, recursive=True):
    ''' workaround for glob, which doesn't match
    files/directories that begin with a "."
    '''
    #wildpath = os.path.abspath(wildcard)
    dirname = os.path.dirname(wildpath)
    basename = os.path.basename(wildpath)

    # set PATH and PATTERN correctly
    if os.path.isdir(wildpath):
        path = wildpath
        pattern = "*"
    else:
        # either basename is file, contains wildcard, or is part of a non-existing path
        path = dirname
        pattern = basename

    if not path:
        path = "."

    if dirname:
        dirname += "/"

    if os.path.exists(path):
        files = os.listdir(path)
        dirname = dirname if return_path else ""

        files = [dirname + name for name in files if fnmatch.fnmatch(name, pattern)]
    else:
        files = []
    return files

def get_local_filenames(path, invert=False):
    '''
    support recursive wildcard searching of files in specified directory.  examples:
        path = "foo"        (return full name of all files in the foo directory)
        path = "foo/*.py"   (return full name of all *.py files in the foo directory)
        path = "foo/**"     (return full name of all files in foo and child folders)
    '''
    files = []
    recursive = False
    wc_target = None

    # remove any relative paths for this search
    base_path = os.path.abspath(".")
    base_len = len(base_path)
    path = os.path.abspath(path)

    # now, can we make it relative to local dir?
    if base_path == path[0:base_len]:
        path = fix_slashes("." + path[base_len:])

    # handle wildcards
    if "*" in path or "?" in path:
        path, wc_target = split_dirname_basename(path)
        if wc_target == "**":
            recursive = True

    # walks the path, top down recursively
    for root, ds, fs in os.walk(path):
        paths = [os.path.join(root, f) for f in fs]

        if wc_target:
            match_value = False if invert else True
            #paths = [path for path in paths if fnmatch.fnmatch(path, wc_target) == match_value]
            paths = [path for path in paths if fnmatch.fnmatch(os.path.basename(path), wc_target) == match_value]

        files += paths

        if not recursive:
            break

    return files, path

def get_local_dirs(path, invert=False):
    '''
    support recursive wildcard searching of subdirs in specified directory.  examples:
        path = "foo"        (return full name of all subdirs in the foo directory)
        path = "foo/my*"    (return full name of all subdirs that begin with "my" in foo directory)
        path = "foo/**"     (return full name of all subdirs in foo, recursively)
    '''
    dirs = []
    recursive = False
    wc_target = None

    # remove any relative paths for this search
    base_path = os.path.abspath(".")
    base_len = len(base_path)
    path = os.path.abspath(path)

    # now, can we make it relative to local dir?
    if base_path == path[0:base_len]:
        path = fix_slashes("." + path[base_len:])

    # handle wildcards
    if "*" in path or "?" in path:
        path, wc_target = split_dirname_basename(path)
        if wc_target == "**":
            recursive = True

    # walks the path, top down recursively
    for root, ds, fs in os.walk(path):
        paths = [os.path.join(root, d) for d in ds]

        if wc_target:
            match_value = False if invert else True
            #paths = [path for path in paths if fnmatch.fnmatch(path, wc_target) == match_value]
            paths = [path for path in paths if fnmatch.fnmatch(os.path.basename(path), wc_target) == match_value]

        dirs += paths

        if not recursive:
            break

    return dirs, path

def get_files_dirs(path_plus):
    '''
    path_plus is a wildcard path, followed by optional ";" and a BFD code string
    BFD code string symbols:
        b - return base name (vs. full path names)
        f - return files
        d - return directories
        s - sort names
        i - invert (find all patterns that don't match)
    '''
    wc_path, codes = path_plus.split(";")

    files = True
    dirs = False

    if "d" in codes:
        dirs = True
        files = False

    if "f" in codes:
        files = True

    items = []
    invert = "i" in codes

    if files:
        files, path = get_local_filenames(wc_path, invert=invert)
        items += files

    if dirs:
        dirs, path = get_local_dirs(wc_path, invert=invert)
        items += dirs

    if "b" in codes:
        items = [os.path.basename(item) for item in items]

    if "s" in codes:
        items.sort()
        #console.print("sorted items=", items)

    return items
    
def make_tmp_dir(prefix, fixed_name=True):
    '''create a temp directory (ensure it is empty)
    :param prefix: specifies a prefix or name to use when naming the temp dir
    :param fixed_name: when fixed_name=True, the prefix will be used to form a fixed 
     path for the directory, and the caller does NOT have to remove the directory after 
     it's usage is completed.  When fixed_name=False, the caller IS responsible for removing the directory. 
    '''
    # :param:
    if fixed_name:
        tmp_dir = os.path.expanduser("~/.xt/tmp/" + prefix)
        ensure_dir_deleted(tmp_dir)
        os.makedirs(tmp_dir)
    else:
        tmp_dir = tempfile.mkdtemp(prefix=prefix)

    return tmp_dir

def fix_slashes(fn, is_linux=None):
    # cannot expand here - we don't know if it is local
    #fn = os.path.expanduser(fn)

    if is_linux is None:
        is_linux = not pc_utils.is_windows()

    if is_linux:
        fn = fn.replace("\\", "/")
        console.detail("fixed slashes for linux: {}".format(fn))
    else:
        if "/run" in fn:
            # protect ws/runxxx entries which are legal XT cmds
            fn = fn.replace("/run", "$$run")
            fn = fn.replace("/", "\\")
            fn = fn.replace("$$run", "/run")
        else:
            fn = fn.replace("/", "\\")
        console.detail("fixed slashes for windows: {}".format(fn))

    return fn

def path_join(*argv, for_windows=False):
    # we cannot rely on os.path.join() since it is designed for the current OS
    # we default to linux (forward slashes) which python makes work in both Linux and Windows
    if for_windows:
        path = "\\".join(argv)
    else:
        path = "/".join(argv)
    return path

def relative_path(path):
    # if path is relative, add a "./" in front on it
    if len(path) > 1:
        if not path[0] in ["\\", "/", ".", "*"] and not path[1] == ":":
            path = "./" + path
    elif not path:
        path = "."
    return path
            
def save(data, fn):
    ensure_dir_exists(file=fn)
    with open(fn, "wb") as outfile:
        pickle.dump(data, outfile)

def load(fn):
    with open(fn, "rb") as infile:
        data = pickle.load(infile)
    return data

def get_xtlib_dir():
    xtlib_dir = os.path.realpath(os.path.dirname(__file__))
    return xtlib_dir

def get_my_file_dir(fn):
    mydir = os.path.realpath(os.path.dirname(fn))
    return mydir    

def root_name(fn):
    basename = os.path.basename(fn)
    root, _ = os.path.splitext(basename)
    return root

def load_yaml(fn): 
    with open(fn, "rt") as file:
        data = yaml.safe_load(file)  # , Loader=yaml.FullLoader)
    return data

def save_yaml(yd, fn): 
    with open(fn, "wt") as file:
        yaml.dump(yd, file)

def copy_tree(src, dst, omit_names=[], omit_dirs=[], dir_callback=None):
    ''' adapted from shutil.copytree but this version
    doesn't require that the dst be empty
    '''
    src = os.path.expanduser(src)
    dst = os.path.expanduser(dst)

    names = os.listdir(src)

    #os.makedirs(dst)
    ensure_dir_exists(dst)

    for name in names:
        if not name in omit_names:
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            
            if os.path.isdir(srcname):
                if not name in omit_dirs:
                    if dir_callback:
                        dir_callback(srcname)
                    copy_tree(srcname, dstname, omit_names, omit_dirs)
            else:
                shutil.copy2(srcname, dstname)

def remove_wildcard(path):
    if has_wildcards(path):
        path = os.path.dirname(path)
    return path

def same_path(path, path2):
    path = remove_wildcard(path)
    path2 = remove_wildcard(path2)
    
    same = os.path.samefile(path, path2)
    return same

def rel_path(path, to_path=None):
    rp = os.path.relpath(path, to_path)
    if rp == "":
        rp = "."

    return rp