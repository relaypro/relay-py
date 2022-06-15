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
if port is None:
    port = 8080

@wf.on_start
async def start_handler(relay, trigger):
    logger.debug(f"mywf trigger={trigger}")

    device_urn = trigger['args']['source_uri']
    logger.debug(f'device_urn is {device_urn}')

    # await relay.terminate()
    await relay.start_interaction(target, 'my interaction')


@wf.on_interaction_lifecycle
async def lifecycle_handler(relay, itype, source_uri, reason):
    if itype == 'started':
        logger.debug('interaction started in app')
        target = relay.targets_from_source_uri(source_uri)
        
        await relay.end_interaction(target, 'myinteraction')
        await relay.terminate()