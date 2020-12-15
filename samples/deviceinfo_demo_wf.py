#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    label = await relay.get_device_label()
    await relay.say(f'This device is {label}')

    try:
        address = await relay.get_device_address()
        await relay.say(f'The device is located at the following street address {address}')

    except WorkflowException:
        await relay.say('failed to get address; is location enabled?')

    try:
        indoor_location = await relay.get_device_indoor_location()
        await relay.say(f"The device's indoor location is {indoor_location}")

    except WorkflowException:
        await relay.say('failed to get indoor location')

    await relay.terminate()

