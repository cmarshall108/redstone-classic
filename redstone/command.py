"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

from twisted.internet import reactor

import redstone.logging as logging
import redstone.util as util
import redstone.packet as packet


class CommandSerializer(object):
    KEYWORD = None
    PERMISSION = None
    DOCUMENTATION = None

    def __init__(self, dispatcher, protocol):
        self._dispatcher = dispatcher
        self._protocol = protocol

    @property
    def protocol(self):
        return self._protocol

    def serialize(self, *args, **kw):
        return None

    def serializeDone(self):
        pass

class CommandMute(CommandSerializer):
    KEYWORD = 'mute'
    PERMISSION = util.PlayerRanks.ADMINISTRATOR
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
    PERMISSION = util.PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Kicks a player for a certain reason.'

    def serialize(self, target, *reason):
        targetEntity = self._protocol.factory.worldManager.getEntityFromUsername(target)

        if not targetEntity:
            return 'Failed to kick unknown player %s' % target

        protocol = targetEntity.protocol

        if not targetEntity:
            return 'Failed to kick player %s!' % target

        protocol.dispatcher.handleDispatch(packet.DisconnectPlayer.DIRECTION, packet.DisconnectPlayer.ID,
            util.joinWithSpaces(reason))

        return 'Successfully kicked player %s!' % targetEntity.name

class CommandSay(CommandSerializer):
    KEYWORD = 'say'
    PERMISSION = util.PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Broadcasts a server message.'

    def serialize(self, *message):
        self._protocol.factory.broadcast(packet.ServerMessage.DIRECTION, packet.ServerMessage.ID, [], self._protocol.entity.id,
            '%s[SERVER]%s: %s' % (util.ChatColors.RED, util.ChatColors.WHITE, util.joinWithSpaces(message)))

        return None

class CommandGoto(CommandSerializer):
    KEYWORD = 'goto'
    PERMISSION = util.PlayerRanks.GUEST
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

        self._protocol.dispatcher.handleDispatch(protocol.ServerIdentification.DIRECTION, protocol.ServerIdentification.ID,
            entity.username, entity=entity, worldName=targetWorld.name)

        return 'Successfully teleported %s to world %s' % (entity.username, targetWorld.name)

class CommandSaveAll(CommandSerializer):
    KEYWORD = 'saveall'
    PERMISSION = util.PlayerRanks.ADMINISTRATOR
    DOCUMENTATION = 'Saves all worlds.'

    def serialize(self):
        for world in self._protocol.factory.worldManager.worlds.values():
            world.save()

        return 'Successfully saved all worlds.'

class CommandSave(CommandSerializer):
    KEYWORD = 'save'
    PERMISSION = util.PlayerRanks.ADMINISTRATOR
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
    PERMISSION = util.PlayerRanks.GUEST
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

        senderEntity.x = targetEntity.x
        senderEntity.y = targetEntity.y
        senderEntity.z = targetEntity.z

        self._protocol.factory.broadcast(packet.PositionAndOrientationStatic.DIRECTION, packet.PositionAndOrientationStatic.ID, [], senderEntity.id, senderEntity.x,
            senderEntity.y, senderEntity.z, senderEntity.yaw, senderEntity.pitch)

        return 'Successfully teleported %s to %s.' % (senderEntity.username, targetEntity.username)

class CommandList(CommandSerializer):
    KEYWORD = 'list'
    PERMISSION = util.PlayerRanks.GUEST
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
    PERMISSION = util.PlayerRanks.GUEST
    DOCUMENTATION = 'Shows the help page.'

    def serialize(self):
        docs = []

        for command in self._dispatcher.commands.values():
            docs.append('> /%s: %s' % (command.KEYWORD, command.DOCUMENTATION))

        return docs

class CommandDispatcher(object):

    def __init__(self, protocol):
        self._dispatchers = {
            CommandMute.KEYWORD: CommandMute(self, protocol),
            CommandKick.KEYWORD: CommandKick(self, protocol),
            CommandSay.KEYWORD: CommandSay(self, protocol),
            CommandGoto.KEYWORD: CommandGoto(self, protocol),
            CommandSaveAll.KEYWORD: CommandSaveAll(self, protocol),
            CommandSave.KEYWORD: CommandSave(self, protocol),
            CommandTeleport.KEYWORD: CommandTeleport(self, protocol),
            CommandList.KEYWORD: CommandList(self, protocol),
            CommandHelp.KEYWORD: CommandHelp(self, protocol),
        }

    @property
    def commands(self):
        return self._dispatchers

    def handleDispatch(self, keyword, args):
        if keyword not in self._dispatchers:
            self.handleDiscard(keyword)
            return 'Couldn\'t execute unknown command %s!' % keyword

        dispatcher = self._dispatchers[keyword]

        if not util.PlayerRanks.hasPermission(dispatcher.protocol.entity, dispatcher.PERMISSION):
            return 'You don\'t have access to that command!'

        try:
            result = dispatcher.serialize(*args)
        except:
            return 'Failed to execute command %s!' % keyword

        return result

    def handleDiscard(self, keyword):
        pass

class CommandParser(object):
    KEYWORD = '/'

    def __init__(self, protocol):
        self._dispatcher = CommandDispatcher(protocol)

    def isCommand(self, message):
        return message.startswith(self.KEYWORD)

    def parse(self, message):
        keywords = message[1:].split(' ')

        if not len(keywords):
            return 'Couldn\'t parse invalid command!'

        return self._dispatcher.handleDispatch(keywords[:1][0], keywords[1:])
