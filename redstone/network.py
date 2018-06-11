"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import urllib
import urllib2

from twisted.internet.protocol import Protocol, ServerFactory
from twisted.internet.task import LoopingCall

import redstone
import redstone.logging as logging
import redstone.util as util
import redstone.packet as packet
import redstone.world as world
import redstone.command as command
import redstone.task as task


class NetworkStatus(object):

    def __init__(self, factory, delay=5.0):
        self._factory = factory
        self._delay = delay

    def setup(self):
        self._update_task = self._factory.add_task('status-update', self.__update,
            priority=-1, delay=self._delay)

    def __update(self, task):
        url = 'http://www.classicube.net/server/heartbeat'
        fields = {
            'port': 25565,
            'max': 1024,
            'name': 'Redstone Classic',
            'public': True,
            'version': 7,
            'salt': self._factory.salt,
            'users': self._factory.worldManager.getNumPlayers(),
            'software': 'Redstone v%s' % redstone.__version__,
        }

        request = urllib2.Request(url, urllib.urlencode(fields))

        try:
            response = urllib2.urlopen(request).read()
        except:
            logging.Logger.debug('Failed to ping server list!')

        return task.wait

class NetworkProtocol(Protocol):

    def __init__(self):
        self._dispatcher = packet.PacketDispatcher(self)
        self._commandParser = command.CommandParser(self)
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
        dataBuffer = util.DataBuffer(data)

        while dataBuffer.remaining:
            self.handleIncoming(dataBuffer)

    def handleIncoming(self, dataBuffer):
        try:
            packetId = dataBuffer.readByte()
        except:
            self.handleDisconnect()
            return

        self._dispatcher.handleDispatch(packet.PacketDirections.DOWNSTREAM,
            packetId, dataBuffer)

    def handleDisconnect(self):
        self.transport.loseConnection()

    def connectionLost(self, reason=None):
        self.factory.removeProtocol(self)

class NetworkFactory(ServerFactory, task.TaskManager):
    protocol = NetworkProtocol

    def __init__(self):
        task.TaskManager.__init__(self)

        self._protocols = []
        self._salt = util.generateRandomSalt()
        self._worldManager = world.WorldManager(self)
        self._status = NetworkStatus(self)

    @property
    def protocols(self):
        return self._protocols

    @property
    def salt(self):
        return self._salt

    @property
    def worldManager(self):
        return self._worldManager

    def startFactory(self):
        logging.Logger.info('Starting up, please wait...')
        self._status.setup()
        self._worldManager.setup()
        logging.Logger.info('Done.')

    def stopFactory(self):
        logging.Logger.info('Shutting down, please wait...')

    def addProtocol(self, protocol):
        if protocol in self._protocols:
            return

        self._protocols.append(protocol)

    def removeProtocol(self, protocol):
        if protocol not in self._protocols:
            return

        if not protocol.entity:
            return

        world = self.worldManager.getWorldFromEntity(protocol.entity.id)
        world.removePlayer(protocol)

        self._protocols.remove(protocol)

    def hasProtocol(self, protocol):
        return protocol in self._protocols

    def broadcast(self, direction, packetId, exceptions, *args, **kwargs):
        for protocol in self._protocols:

            if protocol in exceptions:
                continue

            protocol.dispatcher.handleDispatch(direction, packetId,
                *args, **kwargs)
