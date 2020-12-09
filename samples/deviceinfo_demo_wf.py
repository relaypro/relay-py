#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    name = await relay.get_device_name()
    await relay.say(f'The name of this device is {name}')
    address = await relay.get_device_address()
    await relay.say(f'The device is located at the following street address {address}')
    indoor_location = await relay.get_device_indoor_location()
    await relay.say(f"The device's indoor location is {indoor_location}")
    await relay.terminate()

