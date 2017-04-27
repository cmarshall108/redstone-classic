"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from redstone.util import DataBuffer, clamp
from redstone.logging import Logger as logger

class PacketSerializer(object):
    ID = None
    DIRECTION = None

    def __init__(self, protocol, dispatcher):
        super(PacketSerializer, self).__init__()

        self._protocol = protocol
        self._dispatcher = dispatcher

        # each packet will reassign the data buffer to
        # its packet data buffer and will be sent via the transport buffer.
        self._dataBuffer = DataBuffer()

    @property
    def dataBuffer(self):
        return self._dataBuffer

    def serialize(self, *args, **kw):
        return False

    def serializeDone(self):
        pass

    def deserialize(self, *args, **kw):
        pass

    def deserializeDone(self):
        pass

class SetBlockServer(PacketSerializer):
    ID = 0x06
    DIRECTION = 'upstream'

    def serialize(self, x, y, z, blockType):
        self._dataBuffer.writeShort(x)
        self._dataBuffer.writeShort(y)
        self._dataBuffer.writeShort(z)
        self._dataBuffer.writeByte(blockType)

        return True

class SetBlockClient(PacketSerializer):
    ID = 0x05
    DIRECTION = 'downstream'

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
        if mode == 0:
            blockType = 0x00

        # set the block on the world instance
        world.setBlock(x, y, z, blockType)

        # now broadcast update for the block to all clients
        self._protocol.factory.worldManager.broadcast(world, SetBlockServer.DIRECTION, SetBlockServer.ID, [self._protocol],
            x, y, z, blockType)

class ServerMessage(PacketSerializer):
    ID = 0x0d
    DIRECTION = 'upstream'

    def serialize(self, entityId, message):
        self._dataBuffer.writeSByte(entityId)
        self._dataBuffer.writeString(message)

        return True

class ClientMessage(PacketSerializer):
    ID = 0x0d
    DIRECTION = 'downstream'

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

        if self._protocol.commandParser.isCommand(message):
            response = self._protocol.commandParser.parse(message, entity)

            # do not broadcast the command response send the response
            # only to the local client.
            self._dispatcher.handleDispatch(ServerMessage.DIRECTION, ServerMessage.ID,
                entity.id, response)

            return

        message = '%s: %s' % (entity.username, message)

        logger.info(message)

        self._protocol.factory.broadcast(ServerMessage.DIRECTION, ServerMessage.ID, [],
            entity.id, message)

class PositionAndOrientationStatic(PacketSerializer):
    ID = 0x08
    DIRECTION = 'upstream'

    def serialize(self, entityId, x, y, z, yaw, pitch):
        self._dataBuffer.writeSByte(-1 if entityId == self._protocol.entity.id else entityId)
        self._dataBuffer.writeShort(x * 32.0)
        self._dataBuffer.writeShort(y * 32.0)
        self._dataBuffer.writeShort(z * 32.0)
        self._dataBuffer.writeByte(yaw)
        self._dataBuffer.writeByte(pitch)

        return True

class PositionAndOrientationUpdate(PacketSerializer):
    ID = 0x09
    DIRECTION = 'upstream'

    def serialize(self, entityId, x, y, z, yaw, pitch):
        self._dataBuffer.writeSByte(entityId)
        self._dataBuffer.writeSByte(x)
        self._dataBuffer.writeSByte(y)
        self._dataBuffer.writeSByte(z)
        self._dataBuffer.writeByte(yaw)
        self._dataBuffer.writeByte(pitch)

        return True

class PositionAndOrientation(PacketSerializer):
    ID = 0x08
    DIRECTION = 'downstream'

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

        x = float(x / 32.0)
        y = float(y / 32.0)
        z = float(z / 32.0)

        # update the players x,y,z,yaw,pitch and subtract the current value
        # from the last known value to get the new location change.
        entity = self._protocol.entity

        if not entity:
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

        world = self._protocol.factory.worldManager.getWorldFromEntity(self._protocol.entity.id)

        # the player is moving to fast, teleport them to the x,y,z cordinates
        if changeX < -128 or changeX > 127 or changeY < -128 or changeY > 127 or changeZ < -128 or changeZ > 127:
            self._protocol.factory.worldManager.broadcast(world, PositionAndOrientationStatic.DIRECTION, PositionAndOrientationStatic.ID, [self._protocol],
                entity.id, entity.x, entity.y, entity.z, entity.yaw, entity.pitch)

            return

        self._protocol.factory.worldManager.broadcast(world, PositionAndOrientationUpdate.DIRECTION, PositionAndOrientationUpdate.ID, [self._protocol],
            self._protocol.entity.id if playerId == 255 else playerId, changeX, changeY, changeZ, entity.yaw, entity.pitch)

class DisconnectPlayer(PacketSerializer):
    ID = 0x0e
    DIRECTION = 'upstream'

    def serialize(self, reason):
        self._dataBuffer.writeString(reason)

        return True

    def serializeDone(self):
        # we've just sent a disconnect message to the player,
        # but to make sure the player disconnects drop there connection.
        self._protocol.handleDisconnect()

class DespawnPlayer(PacketSerializer):
    ID = 0x0c
    DIRECTION = 'upstream'

    def serialize(self, entity):
        self._dataBuffer.writeSByte(entity.id)

        return True

class SpawnPlayer(PacketSerializer):
    ID = 0x07
    DIRECTION = 'upstream'

    def serialize(self, entity):
        self._dataBuffer.writeSByte(-1 if entity.id == self._protocol.entity.id else entity.id)
        self._dataBuffer.writeString(entity.username)
        self._dataBuffer.writeShort(entity.x * 32.0)
        self._dataBuffer.writeShort(entity.y * 32.0)
        self._dataBuffer.writeShort(entity.z * 32.0)
        self._dataBuffer.writeByte(entity.yaw)
        self._dataBuffer.writeByte(entity.pitch)

        return True

class LevelFinalize(PacketSerializer):
    ID = 0x04
    DIRECTION = 'upstream'

    def serialize(self):
        world = self._protocol.factory.worldManager.getWorldFromEntity(self._protocol.entity.id)

        self._dataBuffer.writeShort(world.width)
        self._dataBuffer.writeShort(world.height)
        self._dataBuffer.writeShort(world.depth)

        return True

    def serializeDone(self):
        world = self._protocol.factory.worldManager.getWorldFromEntity(self._protocol.entity.id)

        # update all players within the world we're currently going to
        world.updatePlayers(self._protocol)

class LevelDataChunk(PacketSerializer):
    ID = 0x03
    DIRECTION = 'upstream'

    def serialize(self, chunkCount, chunk):
        self._dataBuffer.writeShort(len(chunk))
        self._dataBuffer.writeArray(chunk)
        self._dataBuffer.writeByte(int((100 / len(chunk)) * chunkCount))

        return False

class LevelInitialize(PacketSerializer):
    ID = 0x02
    DIRECTION = 'upstream'

    def serializeDone(self):
        chunk = self._protocol.factory.worldManager.getWorldFromEntity(
            self._protocol.entity.id).serialize()

        chunks = [chunk[i: i + 1024] for i in xrange(0, len(chunk), 1024)]

        for chunkCount, chunk in enumerate(chunks):
            self._dispatcher.handleDispatch(LevelDataChunk.DIRECTION, LevelDataChunk.ID,
                chunkCount, chunk)

        self._dispatcher.handleDispatch(LevelFinalize.DIRECTION, LevelFinalize.ID)

class Ping(PacketSerializer):
    ID = 0x01
    DIRECTION = 'upstream'

    def serialize(self):
        return True

class ServerIdentification(PacketSerializer):
    ID = 0x00
    DIRECTION = 'upstream'

    def serialize(self, username=None, worldName=None):
        self._dataBuffer.writeByte(0x07)
        self._dataBuffer.writeString('A Minecraft classic server!')
        self._dataBuffer.writeString('Welcome to the custom Mineserver!')
        self._dataBuffer.writeByte(0x00)

        if not worldName:
            world = self._protocol.factory.worldManager.getMainWorld()
        else:
            world = self._protocol.factory.worldManager.getWorld(worldName)

        world.addPlayer(self._protocol, username)

        return True

    def serializeDone(self):
        self._dispatcher.handleDispatch(LevelInitialize.DIRECTION, LevelInitialize.ID)

class PlayerIdentification(PacketSerializer):
    ID = 0x00
    DIRECTION = 'downstream'

    def deserialize(self, dataBuffer):
        try:
            protocolVersion = dataBuffer.readByte()
            username = dataBuffer.readString()
        except:
            self._protocol.closeConnection()
            return

        if self._protocol.entity is not None:
            self._dispatcher.handleDispatch(DisconnectPlayer.DIRECTION, DisconnectPlayer.ID,
                'You are already authenticated in game!')

            return

        if self._protocol.factory.worldManager.getEntityFromUsername(username):
            self._dispatcher.handleDispatch(DisconnectPlayer.DIRECTION, DisconnectPlayer.ID,
                'There is already a player logged in with that username!')

            return

        self._dispatcher.handleDispatch(ServerIdentification.DIRECTION, ServerIdentification.ID,
            username=username)

class PacketDispatcher(object):

    def __init__(self, protocol):
        super(PacketDispatcher, self).__init__()

        self._protocol = protocol
        self._packets = {
            'downstream': {
                PlayerIdentification.ID: PlayerIdentification,
                PositionAndOrientation.ID: PositionAndOrientation,
                ClientMessage.ID: ClientMessage,
                SetBlockClient.ID: SetBlockClient,
            },
            'upstream': {
                ServerIdentification.ID: ServerIdentification,
                Ping.ID: Ping,
                LevelInitialize.ID: LevelInitialize,
                LevelDataChunk.ID: LevelDataChunk,
                LevelFinalize.ID: LevelFinalize,
                SpawnPlayer.ID: SpawnPlayer,
                DespawnPlayer.ID: DespawnPlayer,
                PositionAndOrientationStatic.ID: PositionAndOrientationStatic,
                PositionAndOrientationUpdate.ID: PositionAndOrientationUpdate,
                ServerMessage.ID: ServerMessage,
                SetBlockServer.ID: SetBlockServer,
                DisconnectPlayer.ID: DisconnectPlayer,
            }
        }

    def handleDispatch(self, direction, packetId, *args, **kw):
        if direction not in self._packets:
            self.handleDiscard(packetId)
            return

        if packetId not in self._packets[direction]:
            self.handleDiscard(packetId)
            return

        packet = self._packets[direction][packetId](self._protocol, self)

        if direction != packet.DIRECTION:
            return

        # handle the packet by the direction in which the data
        # is traveling, upsteam or downsteam.
        self.handlePacket(packet, packet.DIRECTION, *args, **kw)

    def handlePacket(self, packet, direction, *args, **kw):
        if direction == 'downstream':
            packet.deserialize(*args, **kw)
        elif direction == 'upstream':
            canSendData = packet.serialize(*args, **kw)

            dataBuffer = DataBuffer()
            dataBuffer.writeByte(packet.ID)
            dataBuffer.write(packet.dataBuffer.data)

            self._protocol.transportBuffer.add(dataBuffer.data)

            if canSendData:
                self._protocol.transportBuffer.send()

            # the data has been sent, now give the packer handler
            # a change to send any following data.
            packet.serializeDone()

    def handleDiscard(self, packetId):
        print 'discard packet ', packetId
