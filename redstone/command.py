"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 26th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from redstone.protocol import PositionAndOrientationStatic

class CommandSerializer(object):
    KEYWORD = None

    def __init__(self, protocol, dispatcher):
        super(CommandSerializer, self).__init__()

        self._protocol = protocol
        self._dispatcher = dispatcher

    def serialize(self, *args, **kw):
        pass

    def serializeDone(self):
        pass

class CommandTeleport(CommandSerializer):
    KEYWORD = 'tp'

    def serialize(self, sender, target):
        senderEntity = self._protocol.factory.worldManager.getEntityFromUsername(sender)
        targetEntity = self._protocol.factory.worldManager.getEntityFromUsername(target)

        if not senderEntity:
            return 'Failed to find player %s' % sender

        if not targetEntity:
            return 'Failed to find target player %s' % target

        x = targetEntity.x
        y = targetEntity.y
        z = targetEntity.z
        yaw = senderEntity.yaw
        pitch = senderEntity.pitch

        senderEntity.x = x
        senderEntity.y = y
        senderEntity.z = z

        # teleport the sender entity to the target entity
        self._protocol.factory.broadcast(PositionAndOrientationStatic.DIRECTION, PositionAndOrientationStatic.ID, [],
            senderEntity.id, x, y, z, yaw, pitch)

        return 'Successfully teleported %s to %s' % (sender, target)

class CommandList(CommandSerializer):
    KEYWORD = 'list'

    def serialize(self):
        numPlayerOnline = 0

        for world in self._protocol.factory.worldManager.worlds.values():
            for entity in world.entityManager.entities.values():
                if entity.isPlayer():
                    numPlayerOnline += 1

        return 'There are currently %d players online.' % numPlayerOnline

class CommandDispatcher(object):

    def __init__(self, protocol):
        super(CommandDispatcher, self).__init__()

        self._protocol = protocol
        self._commands = {
            CommandTeleport.KEYWORD: CommandTeleport,
            CommandList.KEYWORD: CommandList,
        }

    def handleDispatch(self, keyword, arguments):
        if keyword not in self._commands:
            return 'Couldn\'t execute unknown command %s!' % keyword

        command = self._commands[keyword](self._protocol, self)

        try:
            result = command.serialize(*arguments)
        except:
            return 'Failed to execute command %s!' % keyword

        return result

    def handleDiscard(self, keyword):
        pass

class CommandParser(object):
    KEYWORD = '/'

    def __init__(self, protocol):
        super(CommandParser, self).__init__()

        self._dispatcher = CommandDispatcher(protocol)

    def isCommand(self, string):
        return string.startswith(self.KEYWORD)

    def parse(self, string):
        keywords = string[1:].split(' ')

        if not len(keywords):
            return 'Couldn\'t parse invalid command!'

        command, = keywords[:1]

        if not len(keywords):
            arguments = []
        else:
            arguments = keywords[1:]

        # attempt to execute the command
        return self._dispatcher.handleDispatch(command, arguments)
