"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import string
import random
import struct


class DataBuffer(object):

    def __init__(self, data=bytes(), offset=0):
        self._data = data
        self._offset = offset

    @property
    def data(self):
        return self._data

    @property
    def offset(self):
        return self._offset

    @property
    def remaining(self):
        return self._data[self._offset:]

    def write(self, data):
        if not len(data):
            return

        self._data += data

    def writeTo(self, fmt, *args):
        self.write(struct.pack('!%s' % fmt, *args))

    def read(self, length):
        data = self._data[self._offset:][:length]
        self._offset += length
        return data

    def clear(self):
        self._data = bytes()
        self._offset = 0

    def readFrom(self, fmt):
        data = struct.unpack_from('!%s' % fmt, self._data, self._offset)
        self._offset += struct.calcsize('!%s' % fmt)
        return data

    def readByte(self):
        return self.readFrom('B')[0]

    def writeByte(self, value):
        self.writeTo('B', value)

    def readSByte(self):
        return self.readFrom('b')[0]

    def writeSByte(self, value):
        self.writeTo('b', value)

    def readShort(self):
        return self.readFrom('h')[0]

    def writeShort(self, value):
        self.writeTo('h', value)

    def readString(self, length=64):
        return self.read(length).strip()

    def writeString(self, string, length=64):
        self.write(string + str().join(['\x20'] * (length - len(string))))

    def readArray(self, length=1024):
        return bytes(self.read(length))

    def writeArray(self, array, length=1024):
        self.write(array + bytes().join(['\x00'] * (length - len(array))))

def clamp(value, minV, maxV):
    return max(minV, min(value, maxV))

def joinWithSpaces(chars):
    out = []

    for char in chars:
        if chars.index(char) == len(char):
            out.append(char)
        else:
            out.append('%s ' % char)

    return ''.join(out)

def generateRandomSalt(length=16):
    alphanumerics = '%s%s%s' % (string.digits, string.uppercase,
        string.lowercase)

    chars = []

    for _ in xrange(length):
        chars.append(random.choice(alphanumerics))

    return ''.join(chars)

class Mouse(object):
    LEFT_CLICK = 0
    RIGHT_CLICK = 1

class ChatColors(object):
    BLACK = '&'
    DARK_BLUE = '&1'
    DARK_GREEN = '&2'
    DARK_TEAL = '&3'
    DARK_RED = '&4'
    PURPLE = '&5'
    GOLD = '&6'
    GRAY = '&7'
    DARK_GRAY = '&8'
    BLUE = '&9'
    BRIGHT_GREEN = '&a'
    TEAL = '&b'
    RED = '&c'
    PINK = '&d'
    YELLOW = '&e'
    WHITE = '&f'

class PlayerRanks(object):
    GUEST = 0
    ADMINISTRATOR = 1

    @classmethod
    def hasPermission(cls, entity, requiredRank):
        if requiredRank == cls.GUEST:
            return True

        if entity.rank != requiredRank:
            return False

        return True

class BlockIds(object):
    AIR = 0
    GRASS = 2
    DIRT = 3
    COBBLESTONE = 4
    WOOD_PLANKS = 5
    SAPLING = 6
    BEDROCK = 7
    FLOWING_WATER = 8
    STATIONARY_WATER = 9
    FLOWING_LAVA = 10
    STATIONARY_LAVA = 11
    SAND = 12
    GRAVEL = 13
    GOLD_ORE = 14
    IRON_ORE = 15
    COAL_ORE = 16

    @classmethod
    def hasBlockId(cls, blockId):
        return True if getattr(cls, blockId) else False
