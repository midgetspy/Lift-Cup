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

from __future__ import with_statement
import os.path
import re
import subprocess
import shlex
import shutil
import sys
import datetime
import glob

from quality import Quality

try:
    from conf import *
except ImportError:
    print "No config found, check that you have a conf.py file"
    sys.exit(1)

LC_VERSION = 0.2

scene_qualities = {Quality.SDTV: "HDTV.XviD",
                   Quality.SDTV: "HDTV.x264",
                   Quality.SDDVD: "DVDRip.XviD",
                   Quality.SDDVD: "DVDRip.x264",
                   Quality.HDTV: "720p.HDTV.x264",
                   Quality.HDWEBDL: "720p.WEB-DL",
                   Quality.FULLHDTV: "1080p.HDTV.x264",
                   Quality.FULLHDWEBDL: "1080p.WEB-DL",
                   Quality.HDBLURAY: "720p.BluRay.x264",
                   Quality.FULLHDBLURAY: "1080p.BluRay.x264",
                   }


class LiftCup(object):

    def __init__(self, full_file_path, quality=None, log=True, test=False, debug=False, cleanup=True, upload=True, skip_quality=False):

        self.tv_dir = os.path.dirname(full_file_path)
        self.file = os.path.basename(full_file_path)
        self.quality = quality
        self.log = log
        self.test = test
        self.debug = debug
        self.cleanup = cleanup
        self.upload = upload
        self.skip_quality = skip_quality
        self.related = False

        # primitive logging
        if self.log:
            if not os.path.isdir(LOG_DIR):
                try:
                    os.makedirs(LOG_DIR)
                except OSError:
                    print "Error:", "No permissions to create ", LOG_DIR
                    sys.exit(1)
            now = datetime.datetime.now()
            self.log_file = open(os.path.join(LOG_DIR, 'lc_log.' + now.strftime("%Y-%m-%d") + '.' + self.file + '.txt'), 'w')

        # if we don't have a valid quality from the config then try to convert the string
        if quality and quality not in Quality.qualityStrings:
            try:
                self.quality = getattr(Quality, quality)
            except AttributeError:
                print "Invalid quality provided, ignoring it:", quality
                self.quality = None

        if self.quality:
            self.logger("Default quality provided:", self.quality)

        # check that our input was sane
        if not os.path.isfile(full_file_path):
            self.logger("Error:", full_file_path, "does not exist.")
            sys.exit(1)

    def logger(self, *args, **kwargs):
        message = str(datetime.datetime.today()) + ' ' + ' '.join([str(x) for x in args])
        if ('debug' not in kwargs or not kwargs['debug']):
            print message
        elif self.debug:
            print message
        if self.log:
            self.log_file.write(message + '\n')

    def execute_command(self, command, cwd=None):
        """
        Executes the given shell command and returns bool representing success.

        command: A string containing the command (with parameters) to execute
        cwd: Optional parameter that gets passed to Popen as the cwd

        Returns: True for success, False for failure.
        """

        # if we have a string turn it into a command list
        if type(command) in (str, unicode):
            # kludge for shlex.split
            if os.sep == '\\':
                command = command.replace(os.sep, os.sep + os.sep)
            script_cmd = shlex.split(command)
        else:
            script_cmd = command

        self.logger("Executing command: " + str(script_cmd), debug=True)

        try:
            if not self.test:
                p = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)
                out, err = p.communicate()
            else:
                out = err = ''
        except OSError, e:
            self.logger("Error:", e)
            return False

        self.logger(out, debug=True)

        if err:
            self.logger(err)

        return True

    def list_associated_files(self, file_path, base_name_only=False, filter_ext=""):
        """
        For a given file path searches for files with the same name but different extension and returns their absolute paths

        file_path: The file to check for associated files
        base_name_only: False add extra '.' (conservative search) to file_path minus extension
        filter_ext: A comma separated string with extensions to include or empty string to include all matches
        Returns: A list containing all files which are associated to the given file
        """

        if not file_path:
            return []

        file_path_list = []
        base_name = file_path.rpartition('.')[0]

        if not base_name_only:
            base_name = base_name + '.'

        # don't strip it all and use cwd by accident
        if not base_name:
            return []

        # don't confuse glob with chars we didn't mean to use
        base_name = re.sub(r'[\[\]\*\?]', r'[\g<0>]', base_name)

        if filter_ext:
            # convert to tuple of extensions to restrict to
            filter_ext = tuple(x.lower().strip() for x in filter_ext.split(','))

        for associated_file_path in glob.glob(base_name + '*'):
            # only add associated to list
            if associated_file_path == file_path:
                continue

            if os.path.isfile(associated_file_path):
                if filter_ext:
                    if associated_file_path.lower().endswith(filter_ext):
                        file_path_list.append(associated_file_path)

                else:
                    file_path_list.append(associated_file_path)

        return file_path_list

    def find_rar_size(self, file_list):
        """
        Picks the size of rars to use for a given release (options are 15, 20, 50, or 100MB).
        Aims for about 30 files in the release.

        Returns: the number of megabytes the rars should be
        """
        rar_sizes = (15, 20, 50, 100)

        # get the size in megs
        size = sum([os.path.getsize(x) for x in file_list]) / 1024 / 1024

        # find the best rar size, aim for about 30 files
        ideal_size = size / 30

        rar_size = min((abs(ideal_size - x), x) for x in rar_sizes)[1]

        return rar_size

    def rar_release(self, path_to_files, rar_dest):
        """
        Rars up the provided files to the given folder.

        path_to_files: A list of full paths to files
        rar_dest: The destination path + base name for the rar set

        Returns: True for success or False for failure
        """

        rar_size = self.find_rar_size(path_to_files)

        common_root_path = os.path.dirname(os.path.commonprefix(path_to_files))
        short_file_list = [x[len(common_root_path) + 1:] for x in path_to_files]
        rar_dest = os.path.abspath(rar_dest)

        self.logger("Creating rarset for " + str(short_file_list) + " at " + rar_dest)
        rar_dir = os.path.dirname(rar_dest)
        if not os.path.isdir(rar_dir):
            os.makedirs(rar_dir)
        cmd = ['rar', 'a', '-v' + str(rar_size) + 'm', '-m0', '-rr1', '-ed', '-dw', rar_dest, ' '.join(short_file_list)]
        # if you wanted to store in rar5 with max compression (against 'rules'):
        # cmd = ['rar', 'a', rar_dest, ' '.join(short_file_list), '-v' + str(rar_size) + 'm', '-m5', '-ma5']

        return self.execute_command(cmd, common_root_path)

    def sfv_release(self, path_to_rars):
        """
        Generates sfv for the rarset.

        path_to_rars: The path + base name for the rar set

        Returns: True for success or False for failure
        """
        self.logger("Creating sfv for " + path_to_rars + "*.rar")
        # cksfv -- need to mimic
        cmd = ['pure-sfv', '-d', '-f', path_to_rars + '*.rar', '-c', path_to_rars + '.sfv']

        return self.execute_command(cmd)

    def create_nfo(self, nfo_path, old_name):
        """
        Generates an NFO file at the given path. Includes the original name of the file for reference.

        nfo_path: Full path of the file we should create
        old_name: The original name of this release before we scenified it
            """
        self.logger("Creating nfo for", nfo_path)
        if os.path.isfile(nfo_path):
            with file(nfo_path, 'r') as original:
                base_nfo = original.read()
        else:
            base_nfo = None
        with file(nfo_path, 'w') as modified:
            modified.write("Original Name: " + old_name + "\n")
            modified.write("Lift Cup " + str(LC_VERSION))
            if base_nfo:
                modified.write("\n" + base_nfo)

    def par_release(self, path_to_rars):
        """
        Generates pars for the rarset.

        path_to_rars: The path + base name for the rar set

        Returns: True for success or False for failure
        """
        self.logger("Creating parset for " + path_to_rars + "*.rar")
        cmd = ['par2create', '-r10', '-n7', path_to_rars, path_to_rars + '*.rar', path_to_rars + '.nfo']

        return self.execute_command(cmd)

    def upload_release(self, release_path):
        """
        Uses newsmangler to upload a set of rars/pars to usenet.

        release_path: The path to the folder containing the rars/pars to upload

        Returns: True for success or False for failure
        """
        self.logger("Uploading the files in", release_path)
        cmd = [POSTER_PY, '-c', POSTER_CONF, release_path + os.sep]

        return self.execute_command(cmd)

    def make_scene_name(self, name):
        """
        Tries to inject the appropriate quality into the name and "scenifies" it a little bit

        name: The original filename of the release

        Returns: A string containing the scenified version of the name
        """
        quality_lookup = Quality.nameQuality(name)
        if quality_lookup != Quality.UNKNOWN or self.skip_quality:
            self.logger("Quality lookup for release is:", Quality.qualityStrings[quality_lookup])
            scene_name = name

        else:
            if not self.quality:
                cur_quality = Quality.assumeQuality(name)
            else:
                cur_quality = self.quality

            base_name, extension = os.path.splitext(name)

            scene_match = re.match('(.*\S)\-(\S+)', base_name)

            if not scene_match:
                scene_name = base_name + '.' + scene_qualities[cur_quality] + extension
            else:
                scene_name = scene_match.group(1) + '.' + scene_qualities[cur_quality] + '-' + scene_match.group(2) + extension

            scene_name = re.sub("[_ !()+'.-]+", '.', scene_name)

        self.logger("Made new scene name:", scene_name)

        return scene_name

    def lift_cup(self):
        cur_file = os.path.join(self.tv_dir, self.file)
        scene_file_name = self.make_scene_name(self.file)
        scene_file_path = os.path.join(TEMP_DIR, scene_file_name)
        scene_base_name = os.path.splitext(scene_file_name)[0]

        if os.path.isfile(scene_file_path):
            self.logger("File", scene_file_path, "already exists, skipping this release")
            return

        if os.path.isdir(os.path.join(TEMP_DIR, scene_base_name)):
            self.logger("Directory", scene_base_name, "already exists, skipping this release")
            return

        # make a copy with the new name
        self.logger("Copying", cur_file, "to temp folder as", scene_file_path)
        if not os.path.isdir(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        shutil.copyfile(cur_file, scene_file_path)
        files_to_rar = [scene_file_path]

        if self.related:
            # make a copy of related files with the new name (limited to subs)
            related_files = self.list_associated_files(cur_file, base_name_only=True, filter_ext="srt,sub,idx")
            for cur_related_file in related_files:
                cur_related_scene_file_name = self.make_scene_name(os.path.basename(cur_related_file))
                cur_related_scene_file_path = os.path.join(TEMP_DIR, cur_related_scene_file_name)
                self.logger("Copying", cur_related_file, "to temp folder as", cur_related_scene_file_path)
                shutil.copyfile(cur_file, cur_related_scene_file_path)
                files_to_rar.append(cur_related_scene_file_path)

        # rar it
        rar_base_name = os.path.join(TEMP_DIR, scene_base_name, scene_base_name)
        if not self.rar_release(files_to_rar, rar_base_name):
            return

        # sfv it
        if not self.sfv_release(rar_base_name):
            return

        # make an nfo if it doesn't exist (some indexers reject non-nfo releases)
        cur_file_name = os.path.splitext(cur_file)[0]
        cur_file_nfo = cur_file_name + '.nfo'
        nfo_file_path = rar_base_name + '.nfo'
        if os.path.isfile(cur_file_nfo):
            self.logger("Using existing nfo at", cur_file_nfo, "as a base")
            shutil.copyfile(cur_file_nfo, nfo_file_path)
        self.create_nfo(nfo_file_path, self.file)

        # par it
        if not self.par_release(rar_base_name):
            return

        # upload it
        if self.upload and not self.upload_release(os.path.dirname(rar_base_name)):
            return

        # remove the leftover files
        if self.cleanup:
            self.logger("Cleaning up leftover files")
            if os.path.isdir(os.path.join(TEMP_DIR, scene_base_name)):
                shutil.rmtree(os.path.join(TEMP_DIR, scene_base_name))

        self.logger("Done.")