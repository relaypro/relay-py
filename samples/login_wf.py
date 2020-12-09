#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    label = await relay.get_var('match_spillover', None)
    if label:
        await relay.say(f'setting the name for this device to {label}')
        await relay.set_device_name(label)

    else:
        await relay.say('I did not get a new name for this device. please login with a name')

