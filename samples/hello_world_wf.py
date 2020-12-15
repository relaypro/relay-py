#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    greeting = await relay.get_var('greeting')
    name = await relay.get_device_label()
    await relay.say('What is your name?')
    user = await relay.listen()
    await relay.say(f'Hello {user}! {greeting} {name}')
    await relay.terminate()

