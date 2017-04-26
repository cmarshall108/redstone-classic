"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

import struct
import gzip
import io
import os
import json
from redstone.logging import Logger as logger
from redstone.entity import Entity, PlayerEntity, EntityManager
from redstone.protocol import SpawnPlayer, DespawnPlayer

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
    WIDTH = 256
    HEIGHT = 64
    DEPTH = 256

    def __init__(self, worldManager, name, blockData=None):
        super(World, self).__init__()

        self._worldManager = worldManager
        self._name = name
        self._entityManager = EntityManager()
        self._blockData = blockData if blockData else self.__generate()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def entityManager(self):
        return self._entityManager

    @property
    def width(self):
        return self.WIDTH

    @property
    def height(self):
        return self.HEIGHT

    @property
    def depth(self):
        return self.DEPTH

    def __generate(self):
        blockData = bytearray(self.WIDTH * self.HEIGHT * self.DEPTH)

        for x in range(self.WIDTH):
            for y in range(self.HEIGHT):
                for z in range(self.DEPTH):
                    blockData[x + self.DEPTH * (z + self.WIDTH * y)] = 0 if y > 32 else \
                        (2 if y == 32 else 3)

        return blockData

    def getBlock(self, x, y, z):
        return self._blockData[x + self.DEPTH * (z + self.WIDTH * y)]

    def setBlock(self, x, y, z, block):
        self._blockData[x + self.DEPTH * (z + self.WIDTH * y)] = block

        # save the data to the world file on block change
        self.save()

    def serialize(self):
        return compress(struct.pack('!I', len(self._blockData)) + bytes(self._blockData))

    def addPlayer(self, protocol, username):
        playerEntity = PlayerEntity()
        playerEntity.id = self._entityManager.allocator.allocate()
        playerEntity.username = username
        playerEntity.world = self.name

        playerEntity.x = 33
        playerEntity.y = 34
        playerEntity.z = 33

        # set the protocols entity object
        protocol.entity = playerEntity

        # add the player entity to the entity manager
        self._entityManager.addEntity(playerEntity)

        logger.info('%s joined world %s' % (playerEntity.username, self.name))

    def removePlayer(self, protocol):
        # remove the protocols entity from the entity manager
        self._entityManager.removeEntity(protocol.entity)

        # update all entities for all players except for the entities owner.
        self._worldManager.broadcast(self, DespawnPlayer.DIRECTION, DespawnPlayer.ID,
            [protocol], protocol.entity)

        logger.info('%s left world %s' % (protocol.entity.username, self.name))

        # remove the entity from the protocol
        protocol.entity = None

    def updatePlayers(self, protocol):
        for (entityId, entity) in self._entityManager.entities.items():
            if entity.world != self.name:
                continue

            protocol.dispatcher.handleDispatch(SpawnPlayer.DIRECTION, SpawnPlayer.ID, entity)

    def updatePlayer(self, protocol):
        # first update our own entity for the client
        protocol.dispatcher.handleDispatch(SpawnPlayer.DIRECTION, SpawnPlayer.ID, protocol.entity)

        # now just broadcast the player to any clients connected, but do not broadcast this packet
        # to the protocol in which owns the player entity.
        self._worldManager.broadcast(self, SpawnPlayer.DIRECTION, SpawnPlayer.ID, [protocol], protocol.entity)

    def save(self):
        self._worldManager.write(self._worldManager.getFilePath(self.name), 'wb',
            self.serialize())

    @staticmethod
    def load(data):
        unpacked = decompress(data)
        payloadLength = struct.unpack('!I', unpacked[:4])[0]
        payload = unpacked[4:]

        if payloadLength != len(payload):
            raise ValueError('Invalid world data file!')

        return bytearray(payload)

class WorldManagerIOError(Exception):
    pass

class WorldManagerIO(object):

    def __init__(self):
        super(WorldManagerIO, self).__init__()

        self._directory = 'worlds'
        self._filename = '%s/properties.json' % self._directory
        self._mainWorldName = 'main'

    def getFilePath(self, worldName):
        return '%s/%s.dat' % (self._directory, worldName)

    def setup(self):
        # first setup the world directory and world properties
        if not os.path.exists(self._directory):
            os.mkdir(self._directory)

        if not os.path.exists(self._filename):
            # setup default world properties
            fields = {
                'worlds': [
                    'main',
                ]
            }

            self.write(self._filename, 'wb', json.dumps(fields,
                indent=4))

        # now read the properties config and setup the worlds
        jsonData = json.loads(self.read(self._filename, 'rb'))

        for worldName in jsonData['worlds']:

            if not os.path.exists(self.getFilePath(worldName)):
                # the world file wasn't found, generate a new world.
                self.create(worldName)
            else:
                # load the world into memory
                self.load(worldName)

    def read(self, filename, mode):
        # open the specified file with the specified file mode
        # read the data, close the file return the data
        data = ''

        with open(filename, mode) as fileobj:
            data = fileobj.read()

            # close the file object instance
            fileobj.close()

        return data

    def write(self, filename, mode, data):
        # open the specified file with the specified file mode
        # and write the data to the file, then close the file.
        with open(filename, mode) as fileobj:
            fileobj.write(data)

            # close the file object instance
            fileobj.close()

    def create(self, worldName):
        logger.info('Creating new world [%s]...' % worldName)

    def load(self, worldName):
        logger.info('Loading world [%s]...' % worldName)

    def delete(self, worldName):
        pass

    def remove(self):
        pass

    def destroy(self):
        pass

class WorldManager(WorldManagerIO):

    def __init__(self, factory):
        super(WorldManager, self).__init__()

        self._factory = factory
        self._worlds = {}

    @property
    def factory(self):
        return self._factory

    def broadcast(self, world, direction, packetId, exceptions, *args, **kw):

        for protocol in self._factory.protocols:
            # since we're broadcasting a specific message from a specific
            # world, we dont want to send data to anyone in a different world.
            if not protocol.entity:
                continue

            if protocol.entity.world != world.name:
                exceptions.append(protocol)

        self._factory.broadcast(direction, packetId, exceptions, *args, **kw)

    def getMainWorld(self):
        return self._worlds[self._mainWorldName]

    def getWorldFromEntity(self, entityId):
        for (worldName, world) in self._worlds.items():
            if not world.entityManager.hasEntity(entityId):
                continue

            return world

        return None

    def getEntityFromWorld(self, entityId):
        for (worldName, world) in self._worlds.items():
            if not world.entityManager.hasEntity(entityId):
                continue

            return world.entityManager.getEntity(entityId)

        return None

    def addWorld(self, world):
        if world.name in self._worlds:
            return

        self._worlds[world.name] = world

    def removeWorld(self, world):
        if world.name not in self._worlds:
            return

        del self._worlds[world.name]

    def getWorld(self, name):
        return self._worlds.get(name)

    def create(self, worldName):
        super(WorldManager, self).create(worldName)

        # setup a new world instance and generate the block data.
        world = World(self, worldName)
        world.save()

        # add the world to the list of active worlds
        self.addWorld(world)

    def load(self, worldName):
        super(WorldManager, self).load(worldName)

        # open the world file and load the world data into memory
        world = World(self, worldName, World.load(self.read(self.getFilePath(worldName), 'rb')))

        # add the world to the list of active worlds
        self.addWorld(world)
