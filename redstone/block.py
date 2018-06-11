"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, April 23rd, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import redstone.util as util
import redstone.packet as packet


class BlockPhysicsManager(object):

    def __init__(self, world):
        self._world = world

    def hasPhysics(self, blockId):
        return blockId == util.BlockIds.SAND or blockId == util.BlockIds.GRAVEL

    def updateBlock(self, x, y, z, blockId):
        if self.hasPhysics(blockId):
            self.updateBlockPhysics(x, y, z, blockId)

    def updateBlockPhysics(self, x, y, z, blockId):
        dy = y - 1

        while self._world.getBlock(x, dy, z) == util.BlockIds.AIR:
            self.broadcastBlockChange(x, dy, z, blockId)

            if self._world.getBlock(x, dy + 1, z) == blockId:
                self.broadcastBlockChange(x, dy + 1, z, util.BlockIds.AIR)

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
        self._world.worldManager.factory.broadcast(packet.SetBlockServer.DIRECTION,
            packet.SetBlockServer.ID, [], x, y, z, blockId)
