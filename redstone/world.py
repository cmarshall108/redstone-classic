"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import struct
import gzip
import io
import os
import json

import redstone.logging as logging
import redstone.entity as entity
import redstone.packet as packet
import redstone.block as block
import redstone.util as util


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
        self._worldManager = worldManager
        self._name = name
        self._entityManager = entity.EntityManager()
        self._physicsManager = block.BlockPhysicsManager(self)
        self._blockData = blockData if blockData else self.__generate()

    @property
    def worldManager(self):
        return self._worldManager

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
    def physicsManager(self):
        return self._physicsManager

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

    def setBlock(self, x, y, z, blockId, update=True):
        self._blockData[x + self.DEPTH * (z + self.WIDTH * y)] = blockId

        # a block has just been placed, tell the physics manager
        # incase the block has physics and needs to be updated
        if update:
            self._physicsManager.updateBlock(x, y, z, blockId)

    def blockInRange(self, x, y, z):
        return x <= self.WIDTH - 1 and x >= 0 and y <= self.HEIGHT - 1 and y >= 0 and z >= 0 and z <= self.DEPTH - 1

    def serialize(self):
        return compress(struct.pack('!I', len(self._blockData)) + bytes(self._blockData))

    def addPlayer(self, protocol, username):
        playerEntity = entity.PlayerEntity(protocol)
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

        logging.Logger.info('%s joined world %s' % (playerEntity.username, self.name))

        # broadcast the player joined message
        protocol.factory.broadcast(packet.ServerMessage.DIRECTION, packet.ServerMessage.ID, [], protocol.entity.id, '%s%s joined the game.%s' % (
            util.ChatColors.BLUE, protocol.entity.username, util.ChatColors.WHITE))

    def removePlayer(self, protocol):
        # remove the protocols entity from the entity manager
        self._entityManager.removeEntity(protocol.entity)

        # free the entity id
        self._entityManager.allocator.deallocate(protocol.entity.id)

        # update all entities for all players except for the entities owner.
        self._worldManager.broadcast(self, packet.DespawnPlayer.DIRECTION, packet.DespawnPlayer.ID,
            [protocol], protocol.entity)

        logging.Logger.info('%s left world %s' % (protocol.entity.username, self.name))

        # broadcast the leaving message
        protocol.factory.broadcast(packet.ServerMessage.DIRECTION, packet.ServerMessage.ID, [], protocol.entity.id, '%s%s left the game.%s' % (
            util.ChatColors.BLUE, protocol.entity.username, util.ChatColors.WHITE))

        # remove the entity from the protocol
        protocol.entity = None

    def updatePlayers(self, protocol):
        for entity in self._entityManager.entities.values():
            if entity.world != self.name or entity.id == protocol.entity.id:
                continue

            protocol.dispatcher.handleDispatch(packet.SpawnPlayer.DIRECTION, packet.SpawnPlayer.ID, entity)

        # now send update for owned entity
        self._worldManager.broadcast(self, packet.SpawnPlayer.DIRECTION, packet.SpawnPlayer.ID, [], protocol.entity)

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
        logging.Logger.info('Creating new world [%s]...' % worldName)

    def load(self, worldName):
        logging.Logger.info('Loading world [%s]...' % worldName)

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

    @property
    def worlds(self):
        return self._worlds

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
        for world in self._worlds.values():
            if not world.entityManager.hasEntity(entityId):
                continue

            return world

        return None

    def getEntityFromWorld(self, entityId):
        for world in self._worlds.values():
            if not world.entityManager.hasEntity(entityId):
                continue

            return world.entityManager.getEntity(entityId)

        return None

    def getEntityFromUsername(self, username):
        for world in self._worlds.values():
            for entity in world.entityManager.entities.values():
                if entity.username == username:
                    return entity

        return None

    def getNumPlayers(self):
        numPlayers = 0

        for world in self._worlds.values():
            for entity in world.entityManager.entities.values():
                if entity.isPlayer():
                    numPlayers += 1

        return numPlayers

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
