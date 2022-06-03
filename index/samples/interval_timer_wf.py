#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    await relay.set_var('tick_num', '1')
    interval = int(await relay.get_var('interval', 60))
    await relay.start_timer(interval)
    await relay.say('starting timer')

@wf.on_button(button='action', taps='single')
async def stop_handler(relay, button, taps):
    await relay.say('stopping timer')
    await relay.terminate()

@wf.on_button
async def button_handler(relay, button, taps):
    await relay.say('dude ! stop pressing buttons')

@wf.on_timer
async def timer_handler(relay):
    num = int(await relay.get_var('tick_num'))
    count = int(await relay.get_var('count', 5))
    if num == count:
        await relay.say('stopping timer')
        await relay.terminate()

    else:
        await relay.say(str(num))
        await relay.set_var('tick_num', str(num+1))

