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
        return blockId == BlockIds.SAND or blockId == BlockIds.GRAVEL

    def updateBlock(self, x, y, z, blockId):
        if self.hasPhysics(blockId):
            self.updateBlockPhysics(x, y, z, blockId)

    def updateBlockPhysics(self, x, y, z, blockId):
        dy = y - 1

        while self._world.getBlock(x, dy, z) == BlockIds.AIR:
            self.broadcastBlockChange(x, dy, z, blockId)

            if self._world.getBlock(x, dy + 1, z) == blockId:
                self.broadcastBlockChange(x, dy + 1, z, BlockIds.AIR)

            dy -= 1
        else:
            dy = y + 1

            if not self._world.blockInRange(x, dy, z):
                return

            blockId = self._world.getBlock(x, dy, z)

            if not self.hasPhysics(blockId):
                return

            self.updateBlockPhysics(x, dy, z, blockId)

    def broadcastBlockChange(self, x, y, z, blockId):

        self._world.setBlock(x, y, z, blockId, False)

        self._world.worldManager.factory.broadcast(SetBlockServer.DIRECTION, SetBlockServer.ID, [], x, y, z, blockId)
