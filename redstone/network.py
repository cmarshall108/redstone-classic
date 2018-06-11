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
from redstone.protocol import PacketDispatcher, DisconnectPlayer, PacketDirections
from redstone.world import WorldManager
from redstone.command import CommandParser

class NetworkPinger(object):

    def __init__(self, factory, delay=1.0):
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

class NetworkProtocol(Protocol):

    def __init__(self):
        self._dispatcher = PacketDispatcher(self)
        self._commandParser = CommandParser(self)
        self._entity = None

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
            self.handleIncoming(dataBuffer)

    def handleIncoming(self, dataBuffer):
        try:
            packetId = dataBuffer.readByte()
        except:
            self.handleDisconnect()
            return

        self._dispatcher.handleDispatch(PacketDirections.DOWNSTREAM, packetId, dataBuffer)

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

    def addProtocol(self, protocol):
        if protocol in self._protocols:
            return

        self._protocols.append(protocol)

    def removeProtocol(self, protocol):
        if protocol not in self._protocols:
            return

        if protocol.entity:
            self.worldManager.getWorldFromEntity(protocol.entity.id).removePlayer(protocol)

        self._protocols.remove(protocol)

    def hasProtocol(self, protocol):
        return protocol in self._protocols

    def broadcast(self, direction, packetId, exceptions, *args, **kw):
        for protocol in self._protocols:
            if protocol in exceptions:
                continue

            protocol.dispatcher.handleDispatch(direction, packetId, *args, **kw)
