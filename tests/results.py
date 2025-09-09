# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import asyncio
import random

import engine
import graphics
import scene

# simulate level scores
for i in range(len(scene.level_scores)):
    scene.level_scores[i] = random.randint(-20, 30)

engine.Results().play()

graphics.main_group.hidden = False

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

asyncio.run(engine_task())
