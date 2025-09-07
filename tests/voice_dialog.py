# SPDX-FileCopyrightText: 2025 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import asyncio

import engine
import graphics

engine.VoiceDialog(
    text="The quick brown fox jumps over the lazy dog. " * 3,
    title="Lorem Ipsum Dolor Sit Amet",
    voice="ozzie",
).play()

graphics.main_group.hidden = False

async def engine_task() -> None:
    while True:
        engine.update()
        await graphics.refresh()

asyncio.run(engine_task())
