"""
 * Copyright (C) Redstone-Crafted (The Redstone Project) - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
 """

from redstone.util import BlockIds
from redstone.protocol import SetBlockServer

class BlockPhysicsManager(object):

    def __init__(self, world):
        self._world = world

    def hasPhysics(self, blockId):
        return blockId == BlockIds.FLOWING_WATER

    def updateBlock(self, x, y, z, blockId):
        if self.hasPhysics(blockId):
            self.updateBlockPhysics(x, y, z, blockId)

    def updateBlockPhysics(self, x, y, z, blockId):
        pass

    def broadcastChange(self, x, y, z, blockId):
        self._world.worldManager.factory.broadcast(SetBlockServer.DIRECTION, SetBlockServer.ID, [],
            x, y, z, blockId)
