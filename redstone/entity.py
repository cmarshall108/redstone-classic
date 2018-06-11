"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import redstone.util as util


class Entity(object):

    def __init__(self, protocol=None):
        self._protocol = protocol
        self._id = 0
        self._x = 0
        self._y = 0
        self._z = 0
        self._yaw = 0
        self._pitch = 0
        self._world = ''

    @property
    def protocol(self):
        return self._protocol

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y):
        self._y = y

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, z):
        self._z = z

    @property
    def yaw(self):
        return self._yaw

    @yaw.setter
    def yaw(self, yaw):
        self._yaw = yaw

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, pitch):
        self._pitch = pitch

    @property
    def world(self):
        return self._world

    @world.setter
    def world(self, world):
        self._world = world

    def isPlayer(self):
        return False

class PlayerEntity(Entity):

    def __init__(self, protocol):
        super(PlayerEntity, self).__init__(protocol)

        self._username = ''
        self._rank = util.PlayerRanks.GUEST
        self._muted = False

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username

    @property
    def rank(self):
        return self._rank

    @rank.setter
    def rank(self, rank):
        self._rank = rank

    @property
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, muted):
        self._muted = muted

    def isPlayer(self):
        return True

class UniqueIdAllocator(object):

    def __init__(self, maxIds=255):
        self._ids = {id: False for id in xrange(maxIds)}

    def allocate(self):
        for id in self._ids:
            if self._ids[id]:
                continue

            self._ids[id] = True
            return id

    def deallocate(self, id):
        if id not in self._ids:
            return

        self._ids[id] = False

class EntityManager(object):

    def __init__(self):
        self._allocator = UniqueIdAllocator()
        self._entities = {}

    @property
    def allocator(self):
        return self._allocator

    @property
    def entities(self):
        return self._entities

    def addEntity(self, entity):
        if entity.id in self._entities:
            return

        self._entities[entity.id] = entity

    def removeEntity(self, entity):
        if entity.id not in self._entities:
            return

        del self._entities[entity.id]

    def hasEntity(self, entityId):
        return entityId in self._entities

    def getEntity(self, entityId):
        return self._entities.get(entityId)
