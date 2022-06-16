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
    
    groupId = await uri.group_id('Main long')
    print(f'GROUP ID: {groupId}')
    groupName = await uri.group_name('Main')
    print(f'GROUP NAME: {groupName}')
    groupNameLong = await uri.group_name('Main Long Name')
    print(f'GROUP NAME LONG: {groupNameLong}')
    deviceName = await uri.device_name('Rabbit')
    print(f'DEVICE NAME: {deviceName}')
    deviceNameLong = await uri.device_name('Rabbit Hole')
    print(f'DEVICE NAME LONG: {deviceNameLong}')
    groupMember = await uri.group_member('Main Long', 'Froggy Frog')
    print(f'GROUP MEMBER: {groupMember}')
    deviceId = await uri.device_id('990003883833883')
    print(f'DEVICE ID: {deviceId}')
    parseGroupName = await uri.parse_group_name('urn:relay-resource:name:group:security%20one')
    print(f'PARSE GROUP NAME: {parseGroupName}')
    parseGroupId = await uri.parse_group_id('urn:relay-resource:id:group:security')
    print(f'PARSE GROUP ID: {parseGroupId}')
    parseDeviceName = await uri.parse_device_name('urn:relay-resource:name:device:jim')
    print(f'PARSE DEVICE NAME: {parseDeviceName}')
    parseDeviceNameInteraction = await uri.parse_device_name('urn:relay-resource:name:interaction:hello%20world?device=urn%3Arelay-resource%3Aname%3Adevice%3ACam')
    print(f'PARSE DEVICE NAME INTERACTION: {parseDeviceNameInteraction}')
    parseDeviceId = await uri.parse_device_id('urn:relay-resource:id:device:990000838383838')
    print(f'PARSE DEVICE ID: {parseDeviceId}')
    isInteractionUri = await uri.is_interaction_uri('urn:relay-resource:name:interaction:hello%20world?device=urn%3Arelay-resource%3Aname%3Adevice%3ACam')
    print(f'IS INTERACTION URI: {isInteractionUri}')
    isRelayUri = await uri.is_relay_uri('urn:relay-resource:id:device:990000838383838')
    print(f'IS RELAY URI: {isRelayUri}')
    isNotInteractionUri = await uri.is_interaction_uri('urn:relay-resource:id:device:990000838383838')
    print(f'IS NOT INTERACTION URI: {isNotInteractionUri}')
    isNotRelayUri = await uri.is_relay_uri('mickey:mouse')
    print(f'IS NOT RELAY URI: {isNotRelayUri}')
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