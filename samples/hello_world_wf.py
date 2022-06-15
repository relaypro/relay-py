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
    
    groupId = await relay.group_id('9900073737373')
    print(f'GROUP ID: {groupId}')
    groupName = await relay.group_name('Main')
    print(f'GROUP NAME: {groupName}')
    groupNameLong = await relay.group_name('Main Long Name')
    print(f'GROUP NAME LONG: {groupNameLong}')
    deviceName = await relay.device_name('Rabbit')
    print(f'DEVICE NAME: {deviceName}')
    deviceNameLong = await relay.device_name('Rabbit Hole')
    print(f'DEVICE NAME LONG: {deviceNameLong}')
    groupMember = await relay.group_member('Main', 'Frog')
    print(f'GROUP MEMBER: {groupMember}')
    deviceId = await relay.device_id('990003883833883')
    print(f'DEVICE ID: {deviceId}')
    parseGroupName = await relay.parse_group_name('urn:relay-resource:name:group:security%20one')
    print(f'PARSE GROUP NAME: {parseGroupName}')
    parseGroupId = await relay.parse_group_id('urn:relay-resource:id:group:security')
    print(f'PARSE GROUP ID: {parseGroupId}')
    parseDeviceName = await relay.parse_device_name('urn:relay-resource:name:device:jim')
    print(f'PARSE DEVICE NAME: {parseDeviceName}')
    parseDeviceNameInteraction = await relay.parse_device_name('urn:relay-resource:name:interaction:hello%20world?device=urn%3Arelay-resource%3Aname%3Adevice%3ACam')
    print(f'PARSE DEVICE NAME INTERACTION: {parseDeviceNameInteraction}')
    parseDeviceId = await relay.parse_device_id('urn:relay-resource:id:device:990000838383838')
    print(f'PARSE DEVICE ID: {parseDeviceId}')
    isInteractionUri = await relay.is_interaction_uri('urn:relay-resource:name:interaction:hello%20world?device=urn%3Arelay-resource%3Aname%3Adevice%3ACam')
    print(f'IS INTERACTION URI: {isInteractionUri}')
    isRelayUri = await relay.is_relay_uri('urn:relay-resource:id:device:990000838383838')
    print(f'IS RELAY URI: {isRelayUri}')
    await relay.terminate()
    # await relay.terminate()
#     await relay.start_interaction(target, 'my interaction')


# @wf.on_interaction_lifecycle
# async def lifecycle_handler(relay, itype, source_uri, reason):
#     if itype == 'started':
#         logger.debug('interaction started in app')
#         target = relay.targets_from_source_uri(source_uri)
        
#         await relay.end_interaction(target, 'myinteraction')
#         await relay.terminate()