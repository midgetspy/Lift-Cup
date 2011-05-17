#!/usr/bin/env python

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

import sys
import os.path
import getopt

from quality import Quality

from lift_cup import LC_VERSION, LiftCup

def usage():
    print "Lift Cup "+str(LC_VERSION)
    print "Usage:", sys.argv[0], "<file path> [quality]"
    print "Options:"
    print " --debug: prints debug info to console instead of just the log"
    print " --test: don't actually execute the commands, just fake it"
    print " --nolog: doesn't create a log file"
    print " --nocleanup: don't delete files after finishing"
    print " --noupload: don't upload files"
    print " --skipquality: don't try to insert quality into the name"
    sys.exit(1)

if __name__ == '__main__':

    # parse out the options from the command line, GNU style
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "dtq::", ['debug', 'test', 'nolog', 'nocleanup', 'noupload', 'quality=', 'skipquality'])
    except getopt.GetoptError:
        usage()
    
    file_path_list = [os.path.abspath(x) for x in args if os.path.isfile(x)]
    
    if not file_path_list:
        print "No valid files specified."
        usage()
    
    DEBUG = False
    TEST = False
    NOLOG = False
    NOCLEANUP = False
    NOUPLOAD = False
    DEFAULT_QUALITY = None
    SKIP_QUALITY = False
    
    for opt, val in opts:
        if opt in ('--debug', '-d'):
            DEBUG = True
        if opt in ('--nolog'):
            NOLOG = True
        if opt in ('--test', '-t'):
            TEST = True
        if opt in ('--nocleanup'):
            NOCLEANUP = True
        if opt in ('--noupload'):
            NOUPLOAD = True
        if opt in ('--quality', '-q'):
            DEFAULT_QUALITY = val
        if opt in ('--skipquality'):
            SKIP_QUALITY = True
    
    for cur_file_path in file_path_list:
        print "Calling Lift Cup for file", cur_file_path 
        lc = LiftCup(cur_file_path, DEFAULT_QUALITY, not NOLOG, TEST, DEBUG, not NOCLEANUP, not NOUPLOAD, SKIP_QUALITY)
        lc.lift_cup()
