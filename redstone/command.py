"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 26th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from redstone.logging import Logger as logger
from redstone.protocol import PositionAndOrientationStatic, ServerIdentification

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

class CommandGoto(CommandSerializer):
    KEYWORD = 'goto'

    def serialize(self, world):
        entity = self._protocol.entity

        if not entity:
            return 'Failed to teleport to world %s!' % world

        targetWorld = self._protocol.factory.worldManager.getWorld(world)

        if not targetWorld:
            return 'Failed to teleport to world, %s doesn\'t exist!' % world

        currentWorld = self._protocol.factory.worldManager.getWorld(entity.world)

        if not currentWorld:
            return 'Failed to teleport to world %s!' % world

        if currentWorld.name == targetWorld.name:
            return 'You cannot teleport to a world you\'re already in!'

        currentWorld.removePlayer(self._protocol)

        # teleport the client to the new world
        self._protocol.dispatcher.handleDispatch(ServerIdentification.DIRECTION, ServerIdentification.ID,
            entity.username, targetWorld.name)

        return 'Successfully teleported %s to world %s' % (entity.username, targetWorld.name)

class CommandSaveAll(CommandSerializer):
    KEYWORD = 'saveall'

    def serialize(self):
        for world in self._protocol.factory.worldManager.worlds.values():
            world.save()

        return 'Successfully saved all worlds.'

class CommandSave(CommandSerializer):
    KEYWORD = 'save'

    def serialize(self):
        entity = self._protocol.entity

        if not entity:
            return 'Failed to save world!'

        world = self._protocol.factory.worldManager.getWorld(entity.world)

        if not world:
            return 'Failed to save world!'

        world.save()
        return 'Successfully saved world %s.' % world.name

class CommandTeleport(CommandSerializer):
    KEYWORD = 'tp'

    def serialize(self, sender, target):
        senderEntity = self._protocol.factory.worldManager.getEntityFromUsername(sender)
        targetEntity = self._protocol.factory.worldManager.getEntityFromUsername(target)

        if not senderEntity:
            return 'Failed to find player %s' % sender

        if not targetEntity:
            return 'Failed to find target player %s' % target

        if senderEntity.id == targetEntity.id:
            return 'You cannot teleport to your self!'

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

        return 'Successfully teleported %s to %s.' % (sender, target)

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
            CommandGoto.KEYWORD: CommandGoto,
            CommandSaveAll.KEYWORD: CommandSaveAll,
            CommandSave.KEYWORD: CommandSave,
            CommandTeleport.KEYWORD: CommandTeleport,
            CommandList.KEYWORD: CommandList,
        }

    def handleDispatch(self, keyword, arguments):
        if keyword not in self._commands:
            self.handleDiscard(keyword)
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

    def parse(self, string, entity):
        keywords = string[1:].split(' ')

        if not len(keywords):
            return 'Couldn\'t parse invalid command!'

        command, = keywords[:1]
        arguments = keywords[1:]

        logger.info('%s issued server command %s' % (entity.username, command))

        # attempt to execute the command
        return self._dispatcher.handleDispatch(command, arguments)
