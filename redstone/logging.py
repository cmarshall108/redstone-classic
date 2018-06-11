"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import sys
import time

from colorama import init
from colorama import Fore, Back, Style

init(autoreset=True)


class Logger(object):

    @staticmethod
    def getTimestamp():
        return time.ctime()

    @classmethod
    def log(cls, color, level, message):
        print >> sys.stdout, '%s[%s][%s]:: %s\r' % (color,
            cls.getTimestamp(), level, message)

    @classmethod
    def info(cls, message):
        cls.log(Fore.GREEN, 'INFO', message)

    @classmethod
    def debug(cls, message):
        cls.log(Fore.BLUE, 'DEBUG', message)

    @classmethod
    def warning(cls, message):
        cls.log(Fore.YELLOW, 'WARNING', message)

    @classmethod
    def error(cls, message):
        cls.log(Fore.RED, 'ERROR', message)
