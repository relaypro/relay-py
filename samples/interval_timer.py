#!/usr/bin/env python

import asyncio
import logging
import logging.config
import yaml

import relay.workflow


with open('logging.yml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)


wf = relay.workflow.Workflow('localhost', 8765)

@wf.on_start
async def start_handler(relay):
    await relay.set_var('tick_num', '1')
    interval = int(await relay.get_var('interval', 60))
    await relay.start_timer(interval)
    await relay.say('starting timer')

@wf.on_button
async def button_handler(relay, button, taps):
    if button == 'action' && taps == 'single':
        await relay.say('stopping timer')
        await relay.terminate()

    else:
        await relay.say('dude ! stop pressing buttons')

@wf.on_timer
async def timer_handler(relay):
    num = int(await relay.get_var('tick_num'))
    count = int(await relay.get_var('count', 5))
    if num == count:
        await relay.say('stopping timer')
        await relay.terminate()

    else:
        await relay.say(str(ticks))
        await relay.set_var('tick_num', str(num+1))


asyncio.get_event_loop().run_forever()

