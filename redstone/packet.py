"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import hashlib
import hmac
import enum

import redstone.util as util
import redstone.logging as logging


class PacketDirections(enum.Enum):
    UPSTREAM = 0
    DOWNSTREAM = 1

class PacketSerializer(object):
    ID = None
    DIRECTION = None

    def __init__(self, dispatcher, protocol):
        self._protocol = protocol
        self._dispatcher = dispatcher

    @property
    def protocol(self):
        return self._protocol

    @property
    def serializable(self):
        return self.serialize if self.DIRECTION == PacketDirections.UPSTREAM else self.deserialize

    @property
    def serializableCallback(self):
        return self.serializeComplete if self.DIRECTION == PacketDirections.UPSTREAM else self.deserializeComplete

    def serialize(self, *args, **kwargs):
        return None

    def serializeComplete(self):
        pass

    def deserialize(self, *args, **kwargs):
        return None

    def deserializeComplete(self):
        pass

class SetBlockServer(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x06

    def serialize(self, x, y, z, blockType):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeShort(x)
        dataBuffer.writeShort(y)
        dataBuffer.writeShort(z)
        dataBuffer.writeByte(blockType)

        return dataBuffer

class SetBlockClient(PacketSerializer):
    DIRECTION = PacketDirections.DOWNSTREAM
    ID = 0x05

    def deserialize(self, dataBuffer):
        try:
            x = dataBuffer.readShort()
            y = dataBuffer.readShort()
            z = dataBuffer.readShort()
            mode = dataBuffer.readByte()
            blockType = dataBuffer.readByte()
        except:
            self._protocol.handleDisconnect()
            return

        world = self._protocol.factory.worldManager.getWorldFromEntity(
            self._protocol.entity.id)

        # todo: use block types instead of hard coded block types.
        if mode == util.Mouse.LEFT_CLICK:
            blockType = util.BlockIds.AIR

        # set the block on the world instance
        world.setBlock(x, y, z, blockType)

        # now broadcast update for the block to all clients
        self._protocol.factory.worldManager.broadcast(world, SetBlockServer.DIRECTION,
            SetBlockServer.ID, [self._protocol], x, y, z, blockType)

class ServerMessage(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x0d

    def serialize(self, entityId, message):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeSByte(entityId)
        dataBuffer.writeString(message)

        return dataBuffer

class ClientMessage(PacketSerializer):
    DIRECTION = PacketDirections.DOWNSTREAM
    ID = 0x0d

    def deserialize(self, dataBuffer):
        try:
            playerId = dataBuffer.readByte()
            message = dataBuffer.readString()
        except:
            self._protocol.handleDisconnect()
            return

        entity = self._protocol.entity

        if not entity:
            return

        if entity.muted:
            return

        if self._protocol.commandParser.isCommand(message):
            response = self._protocol.commandParser.parse(message)

            if not response:
                return

            if isinstance(response, list):
                for message in response:
                    self._dispatcher.handleDispatch(ServerMessage.DIRECTION, ServerMessage.ID,
                        entity.id, message)
            else:
                self._dispatcher.handleDispatch(ServerMessage.DIRECTION, ServerMessage.ID,
                    entity.id, response)

            return

        logging.Logger.info('%s: %s' % (entity.username, message))

        message = '%s: %s' % ('%s%s%s' % (self.getColorFromRank(entity), entity.username, util.ChatColors.WHITE),
            self.sanitize(message))

        self._protocol.factory.broadcast(ServerMessage.DIRECTION, ServerMessage.ID, [],
            entity.id, message)

    def sanitize(self, message):
        # if a client sends an ampersand at the end of the message
        # this can crash the original minecraft classic client
        # remove this character from the end of the message.
        if message.endswith('&'):
            message = message[:len(message) - 1]

        return message

    def getColorFromRank(self, entity):
        if entity.rank == util.PlayerRanks.GUEST:
            return util.ChatColors.DARK_GRAY
        elif entity.rank == util.PlayerRanks.ADMINISTRATOR:
            return util.ChatColors.YELLOW

class PositionAndOrientationStatic(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x08

    def serialize(self, entityId, x, y, z, yaw, pitch):
        if not self._protocol.entity:
            return

        dataBuffer = util.DataBuffer()
        dataBuffer.writeSByte(-1 if entityId == self._protocol.entity.id else entityId)
        dataBuffer.writeShort(x * 32.0)
        dataBuffer.writeShort(y * 32.0)
        dataBuffer.writeShort(z * 32.0)
        dataBuffer.writeByte(yaw)
        dataBuffer.writeByte(pitch)

        return dataBuffer

class PositionAndOrientationUpdate(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x09

    def serialize(self, entityId, x, y, z, yaw, pitch):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeSByte(entityId)
        dataBuffer.writeSByte(x)
        dataBuffer.writeSByte(y)
        dataBuffer.writeSByte(z)
        dataBuffer.writeByte(yaw)
        dataBuffer.writeByte(pitch)

        return dataBuffer

class PositionAndOrientation(PacketSerializer):
    DIRECTION = PacketDirections.DOWNSTREAM
    ID = 0x08

    def deserialize(self, dataBuffer):
        try:
            playerId = dataBuffer.readByte()
            x = dataBuffer.readShort()
            y = dataBuffer.readShort()
            z = dataBuffer.readShort()
            yaw = dataBuffer.readByte()
            pitch = dataBuffer.readByte()
        except:
            self._protocol.handleDisconnect()
            return

        x = x / 32.0
        y = y / 32.0
        z = z / 32.0

        entity = self._protocol.entity

        if not entity:
            return

        world = self._protocol.factory.worldManager.getWorldFromEntity(entity.id)

        if not world:
            return

        changeX = entity.x - x
        changeY = entity.y - y
        changeZ = entity.z - z

        changeX = -changeX * 32.0
        changeY = -changeY * 32.0
        changeZ = -changeZ * 32.0

        entity.x = x
        entity.y = y
        entity.z = z

        changeYaw = entity.yaw - yaw
        changePitch = entity.pitch - pitch

        entity.yaw = yaw
        entity.pitch = pitch

        if self.isOutOfRange(changeX) or self.isOutOfRange(changeY) or self.isOutOfRange(changeZ):
            self._protocol.factory.worldManager.broadcast(world, PositionAndOrientationStatic.DIRECTION, PositionAndOrientationStatic.ID, [self._protocol],
                entity.id, entity.x, entity.y, entity.z, entity.yaw, entity.pitch)

            return

        self._protocol.factory.worldManager.broadcast(world, PositionAndOrientationUpdate.DIRECTION, PositionAndOrientationUpdate.ID, [self._protocol],
            self._protocol.entity.id if playerId == 255 else playerId, changeX, changeY, changeZ, entity.yaw, entity.pitch)

    def isOutOfRange(self, value):
        if value < -128 or value > 127:
            return True

        return False

class DisconnectPlayer(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x0e

    def serialize(self, reason):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeString(reason)

        return dataBuffer

    def serializeComplete(self):
        self._protocol.handleDisconnect()

class DespawnPlayer(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x0c

    def serialize(self, entity):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeSByte(entity.id)

        return dataBuffer

class SpawnPlayer(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x07

    def serialize(self, entity):
        if not self._protocol.entity:
            return

        dataBuffer = util.DataBuffer()
        dataBuffer.writeSByte(-1 if entity.id == self._protocol.entity.id else entity.id)
        dataBuffer.writeString(entity.username)
        dataBuffer.writeShort(entity.x * 32.0)
        dataBuffer.writeShort(entity.y * 32.0)
        dataBuffer.writeShort(entity.z * 32.0)
        dataBuffer.writeByte(entity.yaw)
        dataBuffer.writeByte(entity.pitch)

        return dataBuffer

class LevelFinalize(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x04

    def serialize(self):
        world = self._protocol.factory.worldManager.getWorldFromEntity(
            self._protocol.entity.id)

        dataBuffer = util.DataBuffer()
        dataBuffer.writeShort(world.width)
        dataBuffer.writeShort(world.height)
        dataBuffer.writeShort(world.depth)

        return dataBuffer

    def serializeComplete(self):
        world = self._protocol.factory.worldManager.getWorldFromEntity(
            self._protocol.entity.id)

        world.updatePlayers(self._protocol)

class LevelDataChunk(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x03

    def serialize(self, chunkCount, chunk):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeShort(len(chunk))
        dataBuffer.writeArray(chunk)
        dataBuffer.writeByte(int((100 / len(chunk)) * chunkCount))

        return dataBuffer

class LevelInitialize(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x02

    def serialize(self):
        return util.DataBuffer()

    def serializeComplete(self):
        chunk = self._protocol.factory.worldManager.getWorldFromEntity(
            self._protocol.entity.id).serialize()

        chunks = [chunk[i: i + 1024] for i in xrange(0, len(chunk), 1024)]

        for chunkCount, chunk in enumerate(chunks):
            self._dispatcher.handleDispatch(LevelDataChunk.DIRECTION, LevelDataChunk.ID,
                chunkCount, chunk)

        self._dispatcher.handleDispatch(LevelFinalize.DIRECTION, LevelFinalize.ID)

class Ping(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x01

    def serialize(self):
        return util.DataBuffer()

class ServerIdentification(PacketSerializer):
    DIRECTION = PacketDirections.UPSTREAM
    ID = 0x00

    def serialize(self, username, entity=None, worldName=None):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeByte(0x07)
        dataBuffer.writeString('A Minecraft classic server!')
        dataBuffer.writeString('Welcome to the custom Mineserver!')
        dataBuffer.writeByte(0x00)

        if not worldName:
            world = self._protocol.factory.worldManager.getMainWorld()
        else:
            world = self._protocol.factory.worldManager.getWorld(worldName)

        if entity:
            world.removePlayer(self._protocol)

        world.addPlayer(self._protocol, username)
        return dataBuffer

    def serializeComplete(self):
        self._dispatcher.handleDispatch(LevelInitialize.DIRECTION, LevelInitialize.ID)

class PlayerIdentification(PacketSerializer):
    DIRECTION = PacketDirections.DOWNSTREAM
    ID = 0x00

    def deserialize(self, dataBuffer):
        try:
            protocolVersion = dataBuffer.readByte()
            username = dataBuffer.readString()
            verificationKey = dataBuffer.readString()
            protocolType = dataBuffer.readByte()
        except:
            self._protocol.handleDisconnect()
            return

        if self._protocol.factory.worldManager.getEntityFromUsername(username):
            self._dispatcher.handleDispatch(DisconnectPlayer.DIRECTION, DisconnectPlayer.ID,'There is already a player logged in with that username!')
            return

        digester = hashlib.md5()
        digester.update(self._protocol.factory.salt + username)

        if not hmac.compare_digest(verificationKey, digester.hexdigest()):
            self._dispatcher.handleDispatch(DisconnectPlayer.DIRECTION, DisconnectPlayer.ID, 'Not authenticated with classicube.net!')
            return

        self._dispatcher.handleDispatch(ServerIdentification.DIRECTION, ServerIdentification.ID, username)

class PacketDispatcher(object):

    def __init__(self, protocol):
        self._dispatchers = {
            PacketDirections.DOWNSTREAM: {
                PlayerIdentification.ID: PlayerIdentification(self, protocol),
                PositionAndOrientation.ID: PositionAndOrientation(self, protocol),
                ClientMessage.ID: ClientMessage(self, protocol),
                SetBlockClient.ID: SetBlockClient(self, protocol),
            },
            PacketDirections.UPSTREAM: {
                ServerIdentification.ID: ServerIdentification(self, protocol),
                Ping.ID: Ping(self, protocol),
                LevelInitialize.ID: LevelInitialize(self, protocol),
                LevelDataChunk.ID: LevelDataChunk(self, protocol),
                LevelFinalize.ID: LevelFinalize(self, protocol),
                SpawnPlayer.ID: SpawnPlayer(self, protocol),
                DespawnPlayer.ID: DespawnPlayer(self, protocol),
                PositionAndOrientationStatic.ID: PositionAndOrientationStatic(self, protocol),
                PositionAndOrientationUpdate.ID: PositionAndOrientationUpdate(self, protocol),
                ServerMessage.ID: ServerMessage(self, protocol),
                SetBlockServer.ID: SetBlockServer(self, protocol),
                DisconnectPlayer.ID: DisconnectPlayer(self, protocol),
            }
        }

    def handleSend(self, dispatcher, otherDataBuffer):
        dataBuffer = util.DataBuffer()
        dataBuffer.writeByte(dispatcher.ID)
        dataBuffer.write(otherDataBuffer.data)
        dispatcher.protocol.transport.write(dataBuffer.data)

    def handleDispatch(self, direction, packetId, *args, **kwargs):
        if direction not in self._dispatchers or packetId not in self._dispatchers[direction]:
            self.handleDiscard(direction, packetId)
            return

        self.handleSerializable(self._dispatchers[direction][packetId], *args, **kwargs)

    def handleSerializable(self, dispatcher, *args, **kwargs):
        try:
            otherDataBuffer = dispatcher.serializable(*args, **kwargs)

            if otherDataBuffer:
                self.handleSend(dispatcher, otherDataBuffer)
        finally:
            self.handleSerializableCallback(dispatcher)

    def handleSerializableCallback(self, dispatcher):
        dispatcher.serializableCallback()

    def handleDiscard(self, direction, packetId):
        logging.Logger.warning('Discarding incoming packet %d!' % packetId)
