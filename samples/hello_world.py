#!/usr/bin/env python

import asyncio
import logging
import logging.config
import yaml

import relay.workflow


with open('logging.yml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)


wf = relay.workflow.Workflow('hello')

@wf.on_start
async def start_handler(relay):
    greeting = await relay.get_var('greeting')
    name = await relay.get_device_name()
    await relay.say('What is your name?')
    user = await relay.listen([])
    await relay.say(f'Hello {user}! {greeting} {name}')
    await relay.terminate()


@wf.on_button(button='action', taps='single')
async def handle_action_single_tap(relay, button, taps):
    # button: action, channel
    # taps: single, double, triple
    await relay.say('action button, single tap')


@wf.on_button(button='action')
async def handle_action_button(relay, button, taps):
    await relay.say('action button, any tap')


@wf.on_button(taps='double')
async def handle_single_tap(relay, button, taps):
    await relay.say('any button, double tap')


@wf.on_button
async def handle_button(relay, button, taps):
    await relay.say('any button, any tap')


@wf.on_notification
async def handle_notification(relay, source, event):
    await relay.say(f'Received notification {event} from {source}')


@wf.on_timer
async def handle_timer(relay):
    await relay.say('Received timer event')


server = relay.workflow.Server('localhost', 8765)
server.register(wf, '/hello')
server.start()

