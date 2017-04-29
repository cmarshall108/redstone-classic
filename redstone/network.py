"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

import random
import urllib
import urllib2

from twisted.internet.protocol import Protocol, ServerFactory
from twisted.internet.task import LoopingCall
from redstone.logging import Logger as logger
from redstone.util import DataBuffer
from redstone.protocol import PacketDispatcher, DisconnectPlayer
from redstone.world import WorldManager
from redstone.command import CommandParser

class NetworkPinger(object):

    def __init__(self, factory, delay=25.0):
        self._factory = factory
        self._loopCall = LoopingCall(self.__ping)
        self._loopCall.start(delay)

    def getNumPlayers(self):
        numPlayerOnline = 0

        for world in self._factory.worldManager.worlds.values():
            for entity in world.entityManager.entities.values():
                if entity.isPlayer():
                    numPlayerOnline += 1

        return numPlayerOnline

    def __ping(self):
        url = 'http://www.classicube.net/server/heartbeat'
        fields = {
            'port': 25565,
            'max': 1024,
            'name': 'The Redstone Project Classic Server',
            'public': True,
            'version': 7,
            'salt': self._factory.salt,
            'users': self.getNumPlayers(),
            'software': 'Redstone-Crafted',
        }

        request = urllib2.Request(url, urllib.urlencode(fields))

        try:
            response = urllib2.urlopen(request).read()
        except:
            logger.debug('Failed to ping server list!')

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
        self._commandParser = CommandParser(self)
        self._entity = None

    @property
    def transportBuffer(self):
        return self._transportBuffer

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def commandParser(self):
        return self._commandParser

    @property
    def entity(self):
        return self._entity

    @entity.setter
    def entity(self, entity):
        self._entity = entity

    def connectionMade(self):
        self.factory.addProtocol(self)

    def dataReceived(self, data):
        dataBuffer = DataBuffer(data)

        while len(dataBuffer.remaining):
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
        self._salt = ''
        self._worldManager = WorldManager(self)
        self._pinger = NetworkPinger(self)

    @property
    def protocols(self):
        return self._protocols

    @property
    def salt(self):
        return self._salt

    @salt.setter
    def salt(self, salt):
        self.salt = salt

    def generateSalt(self, length=16):
        return ''.join([random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') \
            for _ in xrange(length)])

    @property
    def worldManager(self):
        return self._worldManager

    def startFactory(self):
        logger.info('Starting up, please wait...')

        self._worldManager.setup()

        # generate a random base62 verification salt
        self.salt = self.generateSalt()

        logger.info('Done.')

    def stopFactory(self):
        logger.info('Shutting down, please wait...')

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
            self.worldManager.getWorldFromEntity(protocol.entity.id).removePlayer(protocol)

        self._protocols.remove(protocol)

    def hasProtocol(self, protocol):
        return protocol in self._protocols

    def disconnect(self):
        # disconnect all players since the server is shutting down.
        self.broadcast(DisconnectPlayer.DIRECTION, DisconnectPlayer.ID, [], 'Server closed.')

    def broadcast(self, direction, packetId, exceptions, *args, **kw):
        for protocol in self._protocols:
            if protocol in exceptions:
                continue

            protocol.dispatcher.handleDispatch(direction, packetId, *args, **kw)
