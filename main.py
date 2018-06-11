"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import sys
import argparse

from twisted.internet import reactor

import redstone
import redstone.network as network


class MinecraftServer(object):

    def __init__(self, backlog, address, port, name, motd, software, public):
        self._backlog = backlog
        self._address = address
        self._port = port
        self._name = name
        self._motd = motd
        self._software = software
        self._public = public

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return self._port

    @property
    def name(self):
        return self._name

    @property
    def motd(self):
        return self._motd

    @property
    def software(self):
        return self._software

    @property
    def public(self):
        return self._public

    def setup(self):
        self._factory = network.NetworkFactory(self)
        reactor.listenTCP(self._port, self._factory, backlog=self._backlog,
            interface=self._address)

    def run(self):
        self._factory.run()
        reactor.run()

def main():
    parser = argparse.ArgumentParser(description='Redstone v%s arguments parser.' % (
        redstone.__version__))

    parser.add_argument('--backlog', type=int, nargs='?',
        help='The maximum amount of allowed TCP connections at once...', default=1024)

    parser.add_argument('--address', type=str, nargs='?',
        help='The address in which the server will bind to...', default='0.0.0.0')

    parser.add_argument('--port', type=int, nargs='?',
        help='The port in which the server will bind to...', default=25565)

    parser.add_argument('--name', type=str, nargs='?',
        help='The name of the server...', default='Redstone Minecraft Server')

    parser.add_argument('--motd', type=str, nargs='?',
        help='The server\'s message of the day...', default='Welcome to the Redstone Minecraft Classic server...')

    parser.add_argument('--software', type=str, nargs='?',
        help='The server\'s software version...', default='Redstone v%s' % redstone.__version__)

    parser.add_argument('--public', type=bool, nargs='?',
        help='Boolean that determines if the server is visible on the public server list...', default=True)

    args = parser.parse_args()

    # create a new minecraft server instance to initialize
    # the protocol factory on...
    server = MinecraftServer(args.backlog, args.address, args.port, args.name,
        args.motd, args.software, args.public)

    # initialize the minecraft server instance
    # which will also initilize any other utilities...
    server.setup()
    server.run()

    return 0

if __name__ == '__main__':
    sys.exit(main())
