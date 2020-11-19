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
    greeting = await relay.get_var('greeting')
    name = await relay.get_device_name()
    await relay.say('What is your name?')
    user = await relay.listen([])
    await relay.say(f'Hello {user}! {greeting} {name}')
    await relay.terminate()


@wf.on_button
async def handle_button(relay, button, taps):
    # button: action, channel
    # taps: single, double, triple
    await relay.say('Please say your name while holding the button down.')


@wf.on_notification
async def handle_notification(relay, source, event):
    await relay.say(f'Received notification {event} from {source}')


@wf.on_timer
async def handle_timer(relay):
    await relay.say('Received timer event')


asyncio.get_event_loop().run_forever()

