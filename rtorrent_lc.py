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

from quality import Quality

from lift_cup import LiftCup

full_file_path = os.path.abspath(sys.argv[1])

DEFAULT_QUALITY = None

# if there's a quality given to us then use it
if len(sys.argv) >= 3:
    if sys.argv[2].upper() == 'SKIP':
        print "Skipping", sys.argv[1]
        sys.exit(0)
    DEFAULT_QUALITY = sys.argv[2].upper()
    
lc = LiftCup(full_file_path, DEFAULT_QUALITY)
lc.lift_cup()
