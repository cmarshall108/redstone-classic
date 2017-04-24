"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

import struct
import gzip
import io

def compress(data, compresslevel=9):
    """Compress data in one shot and return the compressed string.
    Optional argument is the compression level, in range of 1-9.
    """

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=compresslevel) as f:
        f.write(data)

    return buf.getvalue()

def decompress(data):
    """Decompress a gzip compressed string in one shot.
    Return the decompressed string.
    """

    with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:
        data = f.read()

    return data

class World(object):
    WORLD_WIDTH = 256
    WORLD_HEIGHT = 64
    WORLD_DEPTH = 256

    def __init__(self, blockData=None):
        super(World, self).__init__()

        self.blockData = blockData if blockData else self.__generate()

    def __generate(self):
        blockData = bytearray(self.WORLD_WIDTH * self.WORLD_HEIGHT * self.WORLD_DEPTH)

        for x in range(self.WORLD_WIDTH):
            for y in range(self.WORLD_HEIGHT):
                for z in range(self.WORLD_DEPTH):
                    blockData[x + self.WORLD_DEPTH * (z + self.WORLD_WIDTH * y)] = 0 if y > 32 else \
                        (2 if y == 32 else 3)

        return blockData

    def get_block(self, x, y, z):
        return self.blockData[x + self.WORLD_DEPTH * (z + self.WORLD_WIDTH * y)]

    def set_block(self, x, y, z, block):
        self.blockData[x + self.WORLD_DEPTH * (z + self.WORLD_WIDTH * y)] = block

    def serialize(self):
        return compress(struct.pack('!I', len(self.blockData)) + bytes(self.blockData))

    def load(self, data):
        unpacked = decompress(data)
        payloadLength = struct.unpack('!I', unpacked[:4])[0]
        payload = unpacked[4:]

        if payloadLength != len(payload):
            raise ValueError('Invalid world data file!')

        return World(bytearray(payload))
