"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from callbacks import supports_callbacks
from twisted.internet.protocol import Protocol, ServerFactory
from redstone.util import DataBuffer
from redstone.protocol import PacketDispatcher, SpawnPlayer, DespawnPlayer, DisconnectPlayer
from redstone.world import World
from redstone.entity import Entity, PlayerEntity, EntityManager

class NetworkTransportBuffer(object):

    def __init__(self, protocol):
        super(NetworkTransportBuffer, self).__init__()

        self._protocol = protocol

        # stores the list of buffered data in which will
        # be sent all at once using the protocols transport.
        self._buffered = []

        # when the data in the buffer is sent we store the most recent
        # known length of data sent from the buffer in order to flush it.
        self._flushable = 0

    def add(self, data):
        # do not send empty data to the connection, it could
        # potentially cause issues.
        if not len(data):
            return

        # ensure the data isnt already in the buffered
        # list of data to prevent sending the same data over again.
        if data in self._buffered:
            return

        self._buffered.append(bytes(data))

    def remove(self, length):
        # remove the specified length of data in the buffered list
        # this will remove the data starting at the beginning and so forth.
        self._buffered = self._buffered[length:]

    def send(self):
        # join the data in the buffered list into one string
        # object so we can send it over the wire.
        data = bytes().join(self._buffered)

        # since we've just joined all the data, we'll need to
        # flush the buffered list. so store the number of string objects
        # we've joined.
        self._flushable = len(self._buffered)

        # now we're done send the data over the wire using
        # the protocol's transport class.
        self._protocol.transport.write(data)

        # the data has been sent, flush the buffer to prepare
        # for anymore incoming data.
        self.flush()

    def flush(self):
        # before we flush the data from the buffered list
        # first lets make sure we have data to flush.
        if not self._flushable:
            return

        # we've got data to flush from the buffered list,
        # remove the string objects from the list.
        self.remove(self._flushable)

        # flushed the data from the list, reset the flushable int.
        self._flushable = 0

class NetworkProtocol(Protocol):

    def __init__(self):
        self._transportBuffer = NetworkTransportBuffer(self)
        self._dispatcher = PacketDispatcher(self)
        self._entity = None

    @property
    def transportBuffer(self):
        return self._transportBuffer

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def entity(self):
        return self._entity

    @entity.setter
    def entity(self, entity):
        self._entity = entity

    def connectionMade(self):
        self.factory.addProtocol(self)

    def dataReceived(self, data):
        if not len(data):
            return

        self.handleIncoming(DataBuffer(data))

    def handleIncoming(self, dataBuffer):
        try:
            packetId = dataBuffer.readByte()
        except:
            self.handleDisconnect()
            return

        self.handlePacket(packetId, dataBuffer)

    def handlePacket(self, packetId, dataBuffer):
        self._dispatcher.handleDispatch('downstream', packetId, dataBuffer)

    def handleDisconnect(self):
        self.transport.loseConnection()

    def connectionLost(self, reason=None):
        self.factory.removeProtocol(self)

class NetworkFactory(ServerFactory):
    protocol = NetworkProtocol

    def __init__(self):
        self._protocols = []

        self._world = World()
        self._entityManager = EntityManager(self)

    @property
    def world(self):
        return self._world

    @property
    def entityManager(self):
        return self._entityManager

    def startFactory(self):
        pass

    def stopFactory(self):
        # disconnect and remove all players on the server
        self.disconnect()

    def addProtocol(self, protocol):
        if protocol in self._protocols:
            return

        self._protocols.append(protocol)

    def removeProtocol(self, protocol):
        if protocol not in self._protocols:
            return

        # if the protocol has a entity, remove it.
        if protocol.entity is not None:
            self.removePlayer(protocol)

        self._protocols.remove(protocol)

    def addPlayer(self, protocol, username):
        if protocol not in self._protocols or protocol.entity is not None:
            return

        playerEntity = PlayerEntity()
        playerEntity.id = self.entityManager.allocator.allocate()
        playerEntity.username = username

        playerEntity.x = 65
        playerEntity.y = 65
        playerEntity.z = 65

        # set the protocols entity object
        protocol.entity = playerEntity

        # add the player entity to the entity manager
        self._entityManager.addEntity(playerEntity)

    def removePlayer(self, protocol):
        if protocol not in self._protocols or protocol.entity is None:
            return

        # remove the protocols entity from the entity manager
        self._entityManager.removeEntity(protocol.entity)

        # update all entities for all players except for the entities owner.
        self.broadcast(DespawnPlayer.DIRECTION, DespawnPlayer.ID, [protocol], protocol.entity)

        # remove the entity from the protocol
        protocol.entity = None

    def updatePlayers(self, protocol):
        for (entityId, entity) in self._entityManager.entities.items():
            if entity.id == protocol.entity.id:
                continue

            protocol.dispatcher.handleDispatch(SpawnPlayer.DIRECTION, SpawnPlayer.ID, entity)

    def updatePlayer(self, protocol):
        # a protocol requested a new player entity be generated
        # since we must generate the player for the protocol as well
        # so the client knows what entity belongs to it, we need to
        # send a custom packet to the protocol with the entity id set to -1
        # this will tell the client that the entity recieved is it's own.
        protocol.dispatcher.handleDispatch(SpawnPlayer.DIRECTION, SpawnPlayer.ID, protocol.entity)

        # now just broadcast the player to any clients connected, but do not broadcast this packet
        # to the protocol in which owns the player entity.
        self.broadcast(SpawnPlayer.DIRECTION, SpawnPlayer.ID, [protocol], protocol.entity)

    def disconnect(self):
        # disconnect all players since the server is shutting down.
        self.broadcast(DisconnectPlayer.DIRECTION, DisconnectPlayer.ID, [], 'Server closed.')

    def broadcast(self, direction, packetId, exceptions, *args, **kw):
        for protocol in self._protocols:
            if protocol in exceptions:
                continue

            protocol.dispatcher.handleDispatch(direction, packetId, *args, **kw)
