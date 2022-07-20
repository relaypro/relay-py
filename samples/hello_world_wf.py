#!/usr/bin/env python3

# Copyright © 2022 Relay Inc.

import asyncio
import os
import relay.workflow
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

wf = relay.workflow.Workflow('hello')
port = os.getenv('PORT')
if port is None:
    port = 8080

@wf.on_start
async def start_handler(relay, trigger):

    device_urn = trigger['args']['source_uri']
    target = relay.make_target_uris(trigger)

    await relay.start_interaction(target, 'hello world')


@wf.on_interaction_lifecycle
async def lifecycle_handler(relay, itype, interaction_uri, reason):
    if itype == 'started':
        device_name = await relay.get_device_name(interaction_uri)
        await relay.say_and_wait(interaction_uri, 'What is your name?')
        user_provided_name = await relay.listen(interaction_uri, 'request1')
        greeting = await relay.get_var('greeting')
        await relay.say_and_wait(interaction_uri, f'{greeting} {user_provided_name}! You are currently using {device_name}')
        await relay.end_interaction(interaction_uri, 'hello world')
    if itype == 'ended':
        await relay.terminate()

@wf.on_stop
async def stop_handler(relay, reason):
    logger.debug(f'stopped: {reason}')

@wf.on_prompt
async def prompt_handler(relay, source_uri, type):
    logger.debug(f'source uri: {source_uri}, type: {type}')