#!/usr/bin/env python3

import asyncio
import os
import relay.workflow
import logging

import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

wf = relay.workflow.Workflow('hello')
port = os.getenv('PORT')
uri = relay.workflow.Uri
if port is None:
    port = 8080

@wf.on_start
async def start_handler(relay, trigger):
    logger.debug(f"mywf trigger={trigger}")

    device_urn = trigger['args']['source_uri']
    logger.debug(f'device_urn is {device_urn}')
    target = relay.make_target_uris(trigger)

    await relay.start_interaction(target, 'hello world')


@wf.on_interaction_lifecycle
async def lifecycle_handler(relay, itype, source_uri, reason):
    if itype == 'started':
        logger.debug('interaction started in app')
        target = relay.targets_from_source_uri(source_uri)
        name = await relay.get_device_name(target)
        await relay.say_and_wait(target, 'What is your name?')
        user = await relay.listen(target, 'request1')
        await relay.say_and_wait(target, f'Hello {user}! from {name}')
        await relay.end_interaction(target, 'myinteraction')
        await relay.terminate()