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
    name = await relay.get_device_name()
    await relay.say(f'The name of this device is {name}')
    location = await relay.get_device_location()
    await relay.say(f'The device is located at the following street address {location}')
    indoor_location = await relay.get_device_indoor_location()
    await relay.say(f"The device's indoor location is {indoor_location}")
    await relay.terminate()

asyncio.get_event_loop().run_forever()

