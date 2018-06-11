"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import sys
import time


class Logger(object):

    @staticmethod
    def getTimestamp():
        return time.ctime()

    @classmethod
    def log(cls, level, message):
        print >> sys.stdout, '[%s][%s]:: %s\r' % (cls.getTimestamp(), level,
            message)

    @classmethod
    def info(cls, message):
        cls.log('INFO', message)

    @classmethod
    def debug(cls, message):
        cls.log('DEBUG', message)

    @classmethod
    def warning(cls, message):
        cls.log('WARNING', message)

    @classmethod
    def error(cls, message):
        cls.log('ERROR', message)
