"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 26th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from twisted.internet import task, reactor
from redstone.logging import Logger as logger
from redstone.util import PlayerRanks, ChatColors, joinWithSpaces
from redstone.protocol import PositionAndOrientationStatic, ServerIdentification, ServerMessage, DisconnectPlayer

class CommandSerializer(object):
    KEYWORD = None
    PERMISSIONS = None
    DOCUMENTATION = None

    def __init__(self, protocol, dispatcher):
        super(CommandSerializer, self).__init__()

        self._protocol = protocol
        self._dispatcher = dispatcher

    def serialize(self, *args, **kw):
        pass

    def serializeDone(self):
        pass

class CommandMute(CommandSerializer):
    KEYWORD = 'mute'
    PERMISSIONS = PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Mutes a specific player for an amount of time.'

    def serialize(self, target, timeout=None):
        targetEntity = self._protocol.factory.worldManager.getEntityFromUsername(target)

        if not targetEntity:
            return 'Failed to mute/unmute unknown player %s!' % target

        if not targetEntity.isPlayer():
            return 'Failed to mute non player %s!' % target

        if targetEntity.muted:
            targetEntity.muted = False
        else:
            targetEntity.muted = True

        # if a timeout float is specified, thich means we are to unmute
        # the player after a certain amount of time "timeout".
        if timeout is not None:
            try:
                timeout = float(timeout)
            except:
                return 'Failed to mute player %s for %s!' % (target, timeout)

            reactor.callLater(timeout, self.serialize, target)

        return 'Successfully muted %s.' % target

class CommandKick(CommandSerializer):
    KEYWORD = 'kick'
    PERMISSIONS = PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Kicks a player for a certain reason.'

    def serialize(self, target, *reason):
        targetEntity = self._protocol.factory.worldManager.getEntityFromUsername(target)

        if not targetEntity:
            return 'Failed to kick unknown player %s' % target

        protocol = targetEntity.protocol

        if not targetEntity:
            return 'Failed to kick player %s!' % target

        protocol.dispatcher.handleDispatch(DisconnectPlayer.DIRECTION, DisconnectPlayer.ID,
            joinWithSpaces(reason))

        return 'Successfully kicked player %s!' % targetEntity.name

class CommandSay(CommandSerializer):
    KEYWORD = 'say'
    PERMISSIONS = PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Broadcasts a server message.'

    def serialize(self, *message):
        self._protocol.factory.broadcast(ServerMessage.DIRECTION, ServerMessage.ID, [], self._protocol.entity.id,
            '%s[SERVER]%s: %s' % (ChatColors.RED, ChatColors.WHITE, joinWithSpaces(message)))

        return None

class CommandGoto(CommandSerializer):
    KEYWORD = 'goto'
    PERMISSIONS = PlayerRanks.GUEST
    DOCUMENTATION = 'Sends a player to a specific world.'

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
    PERMISSIONS = PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Saves all worlds.'

    def serialize(self):
        for world in self._protocol.factory.worldManager.worlds.values():
            world.save()

        return 'Successfully saved all worlds.'

class CommandSave(CommandSerializer):
    KEYWORD = 'save'
    PERMISSIONS = PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Saves the world your currently in.'

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
    PERMISSIONS = PlayerRanks.GUEST
    DOCUMENTATION = 'Teleports a specific player to another player.'

    def serialize(self, target):
        senderEntity = self._protocol.entity
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
    PERMISSIONS = PlayerRanks.GUEST
    DOCUMENTATION = 'Lists players, worlds currently active.'

    def serialize(self, listType):

        def getPlayers():
            numPlayerOnline = 0

            for world in self._protocol.factory.worldManager.worlds.values():
                for entity in world.entityManager.entities.values():
                    if entity.isPlayer():
                        numPlayerOnline += 1

            return 'There are currently %d players online.' % numPlayerOnline

        def getWorlds():
            worlds = []

            for world in self._protocol.factory.worldManager.worlds.values():
                worlds.append(world.name)

            return ''.join(['%s,' % world for world in worlds])

        if listType == 'players':
            return getPlayers()
        elif listType == 'worlds':
            return getWorlds()

        return 'Unknown command argument specified %s!' % listType

class CommandHelp(CommandSerializer):
    KEYWORD = 'help'
    PERMISSIONS = PlayerRanks.GUEST
    DOCUMENTATION = 'Shows the help page.'

    def serialize(self):
        docs = []

        for command in self._dispatcher.commands.values():
            docs.append('> /%s: %s' % (command.KEYWORD, command.DOCUMENTATION))

        return docs

class CommandDispatcher(object):

    def __init__(self, protocol):
        super(CommandDispatcher, self).__init__()

        self._protocol = protocol
        self._commands = {
            CommandMute.KEYWORD: CommandMute,
            CommandKick.KEYWORD: CommandKick,
            CommandSay.KEYWORD: CommandSay,
            CommandGoto.KEYWORD: CommandGoto,
            CommandSaveAll.KEYWORD: CommandSaveAll,
            CommandSave.KEYWORD: CommandSave,
            CommandTeleport.KEYWORD: CommandTeleport,
            CommandList.KEYWORD: CommandList,
            CommandHelp.KEYWORD: CommandHelp,
        }

    @property
    def commands(self):
        return self._commands

    def handleDispatch(self, keyword, arguments):
        logger.info('%s issued server command %s' % (self._protocol.entity.username, keyword))

        if keyword not in self._commands:
            self.handleDiscard(keyword)
            return 'Couldn\'t execute unknown command %s!' % keyword

        command = self._commands[keyword](self._protocol, self)

        if not PlayerRanks.hasPermission(self._protocol.entity, command.PERMISSIONS):
            return 'You don\'t have access to that command!'

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

        return self._dispatcher.handleDispatch(keywords[:1][0], keywords[1:])
