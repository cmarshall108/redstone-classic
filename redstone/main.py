"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from twisted.internet import reactor
from redstone.network import NetworkFactory

from twisted.internet import reactor

reactor.suggestThreadPoolSize(30)

class MinecraftServer(object):
    reactor = reactor

    def __init__(self):
        self._factory = NetworkFactory()

    def run(self, port=25565):
        self.reactor.listenTCP(port, self._factory)
        self.reactor.run()

if __name__ == '__main__':
    server = MinecraftServer()
    server.run()
