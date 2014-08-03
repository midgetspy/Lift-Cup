# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
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

import os.path
import operator
import re


class Quality:

    NONE = 0               # 0
    SDTV = 1               # 1
    SDDVD = 1 << 1         # 2
    HDTV = 1 << 2          # 4
    RAWHDTV = 1 << 3       # 8  -- 720p/1080i mpeg2 (trollhd releases)
    FULLHDTV = 1 << 4      # 16 -- 1080p HDTV (QCF releases)
    HDWEBDL = 1 << 5       # 32
    FULLHDWEBDL = 1 << 6   # 64 -- 1080p web-dl
    HDBLURAY = 1 << 7      # 128
    FULLHDBLURAY = 1 << 8  # 256

    # put these bits at the other end of the spectrum, far enough out that they shouldn't interfere
    UNKNOWN = 1 << 15      # 32768

    qualityStrings = {NONE: "N/A",
                      UNKNOWN: "Unknown",
                      SDTV: "SD TV",
                      SDDVD: "SD DVD",
                      HDTV: "HD TV",
                      RAWHDTV: "RawHD TV",
                      FULLHDTV: "1080p HD TV",
                      HDWEBDL: "720p WEB-DL",
                      FULLHDWEBDL: "1080p WEB-DL",
                      HDBLURAY: "720p BluRay",
                      FULLHDBLURAY: "1080p BluRay"}

    @staticmethod
    def _getStatusStrings(status):
        toReturn = {}
        for x in Quality.qualityStrings.keys():
            toReturn[Quality.compositeStatus(status, x)] = Quality.statusPrefixes[status] + " (" + Quality.qualityStrings[x] + ")"
        return toReturn

    @staticmethod
    def combineQualities(anyQualities, bestQualities):
        anyQuality = 0
        bestQuality = 0
        if anyQualities:
            anyQuality = reduce(operator.or_, anyQualities)
        if bestQualities:
            bestQuality = reduce(operator.or_, bestQualities)
        return anyQuality | (bestQuality << 16)

    @staticmethod
    def splitQuality(quality):
        anyQualities = []
        bestQualities = []
        for curQual in Quality.qualityStrings.keys():
            if curQual & quality:
                anyQualities.append(curQual)
            if curQual << 16 & quality:
                bestQualities.append(curQual)

        return (anyQualities, bestQualities)

    @staticmethod
    def nameQuality(name):

        name = os.path.basename(name)

        # if we have our exact text then assume we put it there
        for x in sorted(Quality.qualityStrings, reverse=True):
            if x == Quality.UNKNOWN:
                continue

            regex = '\W' + Quality.qualityStrings[x].replace(' ', '\W') + '\W'
            regex_match = re.search(regex, name, re.I)
            if regex_match:
                return x

        checkName = lambda namelist, func: func([re.search(x, name, re.I) for x in namelist])

        if checkName(["(pdtv|hdtv|dsr|tvrip).(xvid|x264)"], all) and not checkName(["(720|1080)[pi]"], all) and not checkName(["hr.ws.pdtv.x264"], any):
            return Quality.SDTV
        elif checkName(["web.dl|webrip", "xvid|x264|h.?264"], all) and not checkName(["(720|1080)[pi]"], all):
            return Quality.SDTV
        elif checkName(["(dvdrip|bdrip)(.ws)?.(xvid|divx|x264)"], any) and not checkName(["(720|1080)[pi]"], all):
            return Quality.SDDVD
        elif checkName(["720p", "hdtv", "x264"], all) or checkName(["hr.ws.pdtv.x264"], any) and not checkName(["(1080)[pi]"], all):
            return Quality.HDTV
        elif checkName(["720p|1080i", "hdtv", "mpeg-?2"], all) or checkName(["1080[pi].hdtv", "h.?264"], all):
            return Quality.RAWHDTV
        elif checkName(["1080p", "hdtv", "x264"], all):
            return Quality.FULLHDTV
        elif checkName(["720p", "web.dl|webrip"], all) or checkName(["720p", "itunes", "h.?264"], all):
            return Quality.HDWEBDL
        elif checkName(["1080p", "web.dl|webrip"], all) or checkName(["1080p", "itunes", "h.?264"], all):
            return Quality.FULLHDWEBDL
        elif checkName(["720p", "bluray|hddvd", "x264"], all):
            return Quality.HDBLURAY
        elif checkName(["1080p", "bluray|hddvd", "x264"], all):
            return Quality.FULLHDBLURAY
        else:
            return Quality.UNKNOWN

    @staticmethod
    def assumeQuality(name):
        if name.lower().endswith((".avi", ".mp4")):
            return Quality.SDTV
        elif name.lower().endswith(".mkv"):
            return Quality.HDTV
        elif name.lower().endswith(".ts"):
            return Quality.RAWHDTV
        else:
            return Quality.UNKNOWN
