"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

class Entity(object):

    def __init__(self):
        super(Entity, self).__init__()

        self._id = 0
        self._x = 0
        self._y = 0
        self._z = 0
        self._yaw = 0
        self._pitch = 0

    def isPlayer(self):
        return False

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

class PlayerEntity(Entity):

    def __init__(self):
        super(PlayerEntity, self).__init__()

        self._username = ''

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username

    def isPlayer(self):
        return True

class UniqueIdAllocator(object):

    def __init__(self, maxIds=255):
        super(UniqueIdAllocator, self).__init__()

        self._id = 0

    def allocate(self):
        self._id += 1; return self._id

    def deallocate(self, id):
        pass

class EntityManager(object):

    def __init__(self, factory):
        super(EntityManager, self).__init__()

        self._factory = factory
        self._allocator = UniqueIdAllocator()
        self._entities = {}

    @property
    def allocator(self):
        return self._allocator

    @property
    def entities(self):
        return self._entities

    def addEntity(self, entity):
        if entity in self._entities:
            return

        self._entities[entity.id] = entity

    def removeEntity(self, entity):
        if entity not in self._entities:
            return

        del self._entities[entity.id]

    def getEntity(self, entityId):
        return self._entities.get(entityId)
