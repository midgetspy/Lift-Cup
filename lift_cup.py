#!/usr/bin/python

# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://github.com/midgetspy/Lift-Cup
#
# This file is part of Lift Cup (adapted from Sick Beard)
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import os
import os.path
import re
import subprocess
import shlex
import shutil
import sys

from quality import Quality

##################### config options #########################

# newsmangler paths
POSTER_PY = '/home/midgetspy/newsmangler/poster.py'
POSTER_CONF = '/home/rascalli/newsmangler/.newsmangler.conf'

# folder to use for temporary storage of rars/etc while we're uploading
TEMP_DIR = '/home/midgetspy/uploads/'

# quality to insert into the name if it doesn't have one already and one isn't provided
DEFAULT_QUALITY = Quality.SDTV

# custom string to insert into NFO file ("" for none)
nfo_string = "Uploaded by rascalli, originally from thebox.bz"

#############################################################

LC_VERSION = 0.1

if len(sys.argv) < 2:
    print "Lift Cup "+str(LC_VERSION)
    print "Usage:", sys.argv[0], "<file path> [quality]"
    print "Options:"
    print " --debug: prints debug info to console instead of just the log"
    print " --nolog: doesn't create a log file"
    print " --test: don't actually execute the commands, just fake it"
    sys.exit(1)

full_file_path = os.path.abspath(sys.argv[1])

TV_DIR = os.path.dirname(full_file_path)
FILE = os.path.basename(full_file_path)

DEBUG = '--debug' in sys.argv
TEST = '--test' in sys.argv
NOLOG = '--nolog' in sys.argv

# primitive logging
if NOLOG:
    log_file = open('lc_log.'+FILE+'.txt', 'w')
def log(*args, **kwargs):
    message = ' '.join([str(x) for x in args])
    if 'debug' not in kwargs or not kwargs['debug']:
        print message
    if NOLOG:
        log_file.write(message+'\n')

# check that our input was sane
if not os.path.isfile(full_file_path):
    log("Error:", full_file_path, "does not exist.")
    sys.exit(1)

scene_qualities = {Quality.SDTV: "HDTV.XviD",
           Quality.SDDVD: "DVDRip.XviD",
           Quality.HDTV: "720p.HDTV.x264",
           Quality.HDWEBDL: "720p.WEB-DL",
           Quality.HDBLURAY: "720p.BluRay.x264",
           Quality.FULLHDBLURAY: "1080p.BluRay.x264",
          }

# if there's a quality given to us then use it
if len(sys.argv) >= 3:
    if sys.argv[2].upper() == 'SKIP':
        log("Skipping", sys.argv[1])
        sys.exit(0)

    try:
        new_quality = getattr(Quality, sys.argv[2].upper())
        log("Default quality provided:", sys.argv[2].upper())
        DEFAULT_QUALITY = new_quality
    except AttributeError:
        pass


def replace_extension(filename, newext):
    """
    Replaces the extension of the given filename with a new extension.

    filename: Name of the file to replace the extension for
    newext: New extension to use

    Returns: The filename with the new extension
    """
    if '.' not in filename:
        return filename

    return os.path.splitext(filename)[0]+'.'+newext

def execute_command(command):
    """
    Executes the given shell command and returns bool representing success.

    command: A string containing the command (with parameters) to execute

    Returns: True for success, False for failure.
    """

    script_cmd = shlex.split(command)
    log("Executing command "+str(script_cmd), debug=True)

    try:
        if TEST:
            p = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out, err = p.communicate()
        else:
            out = err = ''
    except OSError, e:
        log("Error:", e)
        return False

    if DEBUG:
        log(out, debug=True)

    if err:
        log(err)

    return True

def rar_release(path_to_files, rar_dest):
    """
    Rars up the provided files to the given folder.
    
    path_to_files: A list of full paths to files
    rar_dest: The destination path + base name for the rar set
    
    Returns: True for success or False for failure
    """

    log("Creating rars for "+str(path_to_files)+" at "+rar_dest)
    rar_dir = os.path.dirname(rar_dest)
    if not os.path.isdir(rar_dir):
        os.makedirs(rar_dir)
    cmd = "rar a %s %s -v15m -m0" % (rar_dest, ' '.join(path_to_files))
    
    return execute_command(cmd)

def par_release(path_to_rars):
    """
    Generates pars for a set of rars.
    
    path_to_rars: The path + base name for the rar set
    
    Returns: True for success or False for failure
    """
    log("Creating pars for rars at "+path_to_rars+"*.rar")

    cmd = "par2create -r10 -n7 %s %s" % (path_to_rars, path_to_rars+'*.rar')

    return execute_command(cmd)

def upload_release(release_path):
    """
    Uses newsmangler to upload a set of rars/pars to usenet.
    
    release_path: The path to the folder containing the rars/pars to upload
    
    Returns: True for success or False for failure
    """
    log("Uploading the files in", release_path)
    cmd = POSTER_PY + ' -c '+ POSTER_CONF + ' ' + release_path

    return execute_command(cmd)

def make_scene_name(name):
    """
    Tries to inject the appropriate quality into the name and "scenifies" it a little bit
    
    name: The original filename of the release
    
    Returns: A string containing the scenified version of the name
    """
    if Quality.nameQuality(name) != Quality.UNKNOWN:
        scene_name = name
    
    else:
        base_name, extension = os.path.splitext(name)

        if '-' not in base_name:
            scene_name = base_name + '.' + scene_qualities[DEFAULT_QUALITY] + extension
        else:
            root_scene_name, partition, scene_group = base_name.rpartition('-')
            scene_name = root_scene_name + '.' + scene_qualities[DEFAULT_QUALITY] + '-' + scene_group + extension

    scene_name = re.sub("[_ !()+']", '.', scene_name)

    log("Made new scene name:", scene_name)

    return scene_name

def create_nfo(nfo_path, old_name):
    """
    Generates an NFO file at the given path. Includes the original name of the file for reference.
    
    nfo_path: Full path of the file we should create
    old_name: The original name of this release before we scenified it
        """
    log("Creating NFO at", nfo_path)
    nfo = open(nfo_path, 'w')
    nfo.write('Original name: '+old_name+'\n')
    if nfo_string:
        nfo.write(nfo_string+'\n')
    nfo.write('Lift Cup '+str(LC_VERSION)+'\n')
    nfo.close

def main():
    cur_file = os.path.join(TV_DIR, FILE)
    scene_file_name = make_scene_name(FILE)
    scene_file_path = os.path.join(TEMP_DIR, scene_file_name)

    if os.path.isfile(scene_file_path):
        return
    
    # make a copy with the new name
    log("Copying", cur_file, "to temp folder as", scene_file_path)
    if not os.path.isdir(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    shutil.copyfile(cur_file, scene_file_path)

    # make an nfo
    scene_base_name = os.path.splitext(scene_file_name)[0]
    nfo_file_path = replace_extension(scene_file_path, 'nfo')
    create_nfo(nfo_file_path, FILE)

    # rar the avi and nfo
    rar_base_name = os.path.join(TEMP_DIR, scene_base_name, scene_base_name)
    files_to_rar = [scene_file_path, replace_extension(scene_file_path, 'nfo')]
    if not rar_release(files_to_rar, rar_base_name):
        return

    # par it
    if not par_release(rar_base_name):
        return

    # upload it
    if not upload_release(os.path.dirname(rar_base_name)):
        return

    # remove the leftover files
    log("Cleaning up leftover files")
    os.remove(scene_file_path)
    os.remove(nfo_file_path)
    shutil.rmtree(os.path.join(TEMP_DIR, scene_base_name))

    

main()
