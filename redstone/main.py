"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from twisted.internet import reactor
from redstone.network import NetworkFactory

class MinecraftServer(object):

    def __init__(self):
        self._factory = NetworkFactory()

    def run(self, port=25565):
        reactor.listenTCP(port, self._factory)
        reactor.run()

if __name__ == '__main__':
    server = MinecraftServer()
    server.run()
