"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from struct import pack, unpack_from, calcsize

class DataBuffer(object):

    def __init__(self, data=bytes(), offset=0):
        super(DataBuffer, self).__init__()

        self._data = data
        self._offset = offset

    @property
    def data(self):
        return self._data

    @property
    def offset(self):
        return self._offset

    def write(self, data):
        if not len(data):
            return

        self._data += data

    def writeTo(self, fmt, *args):
        self.write(pack('!%s' % fmt, *args))

    def read(self, length):
        data = self._data[self._offset:][:length]
        self._offset += length
        return data

    def readFrom(self, fmt):
        data = unpack_from('!%s' % fmt, self._data, self._offset)
        self._offset += calcsize('!%s' % fmt)
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
        return self.read(length).encode('utf-8').strip()

    def writeString(self, string, length=64):
        outString = string.encode('utf-8')

        if len(outString) > length:
            outString = outString[:length]

        for _ in xrange(length - len(outString)):
            outString += '\x20'

        self.write(outString)

    def writeArray(self, byteArray, length=1024):
        outByteArray = bytes(byteArray)

        if len(outByteArray) > length:
            outByteArray = outByteArray[:length]

        for _ in xrange(length - len(outByteArray)):
            outByteArray += '\x00'

        self.write(outByteArray)

def clamp(value, minV, maxV):
    return max(minV, min(value, maxV))
