
# Copyright © 2022 Relay Inc.

import asyncio
import json
import logging
import time
import uuid
import websockets
import sys
import time
import platform
import os
import urllib.parse
import requests
import ssl
from functools import singledispatch

logging.basicConfig(format='%(levelname)s: %(asctime)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# without a specific handler, it will log to the console. Uncomment below to not send to console.
# logger.addHandler(logging.NullHandler())

version = "relay-sdk-python/2.0.0"
server_hostname = "all-main-qa-ibot.nocell.io"
# server_hostname = "all-main-pro-ibot.nocell.io"
auth_hostname = "auth.relaygo.info"
# auth_hostname = "auth.relaygo.com"

class Server:
    """Initializes the host and port in which the workflow will run,
    registers the workflow on a path, handles ssl protocol, and listens
    for a workflow trigger.
    """
    def __init__(self, host:str, port:int, **kwargs):
        """Initializes the host and port, checks ssl.

        Args:
            host (str): host for the workflow.
            port (int): the port to listen for a trigger.
        """
        self.host = host
        self.port = port
        self.workflows = {}   # {path: workflow}
        for key in kwargs:
            if key == 'ssl_key_filename':
                self.ssl_key_filename = kwargs[key]
            elif key == 'ssl_cert_filename':
                self.ssl_cert_filename = kwargs[key]

    def register(self, workflow, path:str):
        """Registers a workflow on the path.

        Args:
            workflow: the workflow to be registered.
            path (str): the path on which the workflow will be registered.

        Raises:
            ServerException: thrown when a workflow is already registered on that path.
        """
        if path in self.workflows:
            raise ServerException(f'a workflow is already registered at path {path}')
        self.workflows[path] = workflow

    def start(self):
        """
        Starts ssl protocol and then listens on the server for a workflow trigger.

        Raises:
            ServerException: thrown when the ssl_cert_file cannot be read.
            ServerException: thrown when the ssl_key_file cannot be read.
        """

        uname_result = platform.uname()
        custom_headers = { 'User-Agent': f'{version} (Python {platform.python_version()}; {uname_result.system} {uname_result.machine} {uname_result.release})' }
        if hasattr(self, 'ssl_key_filename') and hasattr(self, 'ssl_cert_filename') :
            if not os.access(self.ssl_cert_filename, os.R_OK):
                raise ServerException(f"can't read ssl_cert_file {ssl_cert_filename}")
            if not os.access(self.ssl_key_filename, os.R_OK):
                raise ServerException(f"can't read ssl_key_file {ssl_key_filename}")
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self.ssl_cert_filename, self.ssl_key_filename)
            start_server = websockets.serve(self.handler, self.host, self.port, extra_headers=custom_headers, ssl=ssl_context)
            logger.info(f'Relay workflow server ({version}) listening on {self.host} port {self.port} with ssl_context {ssl_context}')
        else:
            start_server = websockets.serve(self.handler, self.host, self.port, extra_headers=custom_headers)
            logger.info(f'Relay workflow server ({version}) listening on {self.host} port {self.port} with plaintext')

        asyncio.get_event_loop().run_until_complete(start_server)

        try:
            asyncio.get_event_loop().run_forever()

        except KeyboardInterrupt:
            logger.debug('server terminated')

    async def handler(self, websocket, path:str):
        """Handles a request on a path.

        Args:
            websocket: websocket protocol.
            path (str): path that contained the request.
        """
        workflow = self.workflows.get(path, None)
        if workflow:
            logger.debug(f'handling request on path {path}')
            relay = Relay(workflow)
            await relay.handle(websocket)

        else:
            logger.warning(f'ignoring request for unregistered path {path}')
            await websocket.close()


class ServerException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

# Helper constants and methods for creating and parsing out a URN.

# The scheme used for creating a URN.
SCHEME = 'urn'

# The root used for creating a URN.
ROOT = 'relay-resource'

# Used to specify that the URN is for a group.
GROUP = 'group'

# Used to specify that the URN is for an ID.
ID = 'id'

# Used to specify that the URN is for a name.
NAME = 'name'

# Used to specify that the URN is for a device.
DEVICE = 'device'

# Pattern used when creating an interaction URN.
DEVICE_PATTERN = '?device='

# Beginning of an interaction URN that uses the name of a device.
INTERACTION_URI_NAME = 'urn:relay-resource:name:interaction'

# Beginning of an interaction URN that uses the ID of a device.
INTERACTION_URI_ID = 'urn:relay-resource:id:interaction'

def construct(resource_type:str, id_type:str, id_or_name:str):
    """Constructs a URN based off of the resource type, id type, and
    id/name.  Used by methods that need to create a URN when given a
    name or ID of a device or group.

    Args:
        resource_type (str): indicates whether the URN is for a device, group, or interaction.
        id_type (str): indicates whether the URN has an ID type of 'name' or 'ID'.
        id_or_name (str): the id or name of the device or group.

    Returns:
        str: the newly constructed URN.
    """
    return f'{SCHEME}:{ROOT}:{id_type}:{resource_type}:{id_or_name}'

def group_id(id:str):
    """Creates a URN from a group ID.

    Args:
        id (str): the ID of the group.

    Returns:
        str: the newly constructed URN.
    """
    return construct(GROUP, ID, urllib.parse.quote(id))

def group_name(name:str):
    """Creates a URN from a group name.

    Args:
        name (str): the name of the group.

    Returns:
        str: the newly constructed URN.
    """
    return construct(GROUP, NAME, urllib.parse.quote(name))

def device_name(name:str):
    """Creates a URN from a device name.

    Args:
        name (str): the name of the device.

    Returns:
        str: the newly constructed URN.
    """
    return construct(DEVICE, NAME, urllib.parse.quote(name))

def group_member(group:str, device:str):
    """Creates a URN for a group member.

    Args:
        group (str): the name of the group that the device belongs to.
        device (str): the device ID or name.

    Returns:
        str: the newly constructed URN.
    """
    return f'{SCHEME}:{ROOT}:{NAME}:{GROUP}:{urllib.parse.quote(group)}{DEVICE_PATTERN}' + urllib.parse.quote(f'{SCHEME}:{ROOT}:{NAME}:{DEVICE}:{device}')

def device_id(id:str):
    """Creates a URN from a device ID.

    Args:
        id (str): the ID of the device.

    Returns:
        str: the newly constructed URN.
    """
    return construct(DEVICE, ID, urllib.parse.quote(id))

def parse_group_name(uri:str):
    """Parses out a group name from a group URN.

    Args:
        uri (str): the URN that you would like to extract the group name from.

    Returns:
        str: the group name.
    """
    scheme, root, id_type, resource_type, name = urllib.parse.unquote(uri).split(':')
    if id_type == NAME and resource_type == GROUP:
        return name
    logger.error('invalid group urn')
    
def parse_group_id(uri:str):
    """Parses out a group ID from a group URN. 

    Args:
        uri (str): the URN that you would like to extract the group ID from.

    Returns:
        str: the group ID.
    """
    scheme, root, id_type, resource_type, id = urllib.parse.unquote(uri).split(':')
    if id_type == ID and resource_type == GROUP:
        return id
    logger.error('invalid group urn')

def parse_device_name(uri:str):
    """Parses out a device name from a device or interaction URN.

    Args:
        uri (str): the device or interaction URN that you would like to extract the device name from.

    Returns:
        str: the device name.
    """
    uri = urllib.parse.unquote(uri)
    if not is_interaction_uri(uri):
        scheme, root, id_type, resource_type, name = uri.split(':')
        if id_type == NAME:
            return name
    elif is_interaction_uri(uri):
        scheme, root, id_type, resource_type, i_name, i_root, i_id_type, i_resource_type, name = uri.split(':')
        if id_type == NAME and i_id_type == NAME:
            return name
    logger.error('invalid device urn')

def parse_device_id(uri:str):
    """Parses out a device ID from a device or interaction URN.

    Args:
        uri (str): the device or interaction URN that you would like to extract the device ID from.

    Returns:
        str: the device ID.
    """
    uri = urllib.parse.unquote(uri)
    if not is_interaction_uri(uri):
        scheme, root, id_type, resource_type, id = uri.split(':')
        if id_type == ID:
            return id
    elif is_interaction_uri(uri):
        scheme, root, id_type, resource_type, i_id, i_root, i_id_type, i_resource_type, id = uri.split(':')
        if id_type == ID and i_id_type == ID:
            return id
    logger.error('invalid device urn')

def parse_interaction(uri:str):
    """Parses out the name of an interaction from an interaction URN.

    Args:
        uri (str): the interaction URN that you would like to parse the interaction from.

    Returns:
        str: the name of an interaction.
    """
    uri = urllib.parse.unquote(uri)
    if is_interaction_uri(uri):
        scheme, root, id_type, resource_type, i_name, i_root, i_id_type, i_resource_type, name = uri.split(':')
        interaction_name, discard = i_name.split('?') 
        return interaction_name
    logger.error('not an interaction urn')

def is_interaction_uri(uri:str):
    """Checks if the URN is for an interaction.

    Args:
        uri (str): the device URN.

    Returns:
        bool: true if the URN is an interaction URN, false otherwise.
    """
    if INTERACTION_URI_NAME in uri or INTERACTION_URI_ID in uri:
        return True
    return False

def is_relay_uri(uri:str):
    """Checks if the URN is a Relay URN.

    Args:
        uri (str): the device, group, or interaction URN.

    Returns:
        bool: true if the URN is a Relay URN, false otherwise.
    """
    if uri.startswith(f'{SCHEME}:{ROOT}'):
        return True
    return False

class Workflow:
    
    def __init__(self, name:str):
        self.name = name
        self.type_handlers = {}  # {(type, args): func}

    def on_start(self, func):
        self.type_handlers[('wf_api_start_event')] = func

    def on_stop(self, func):
        self.type_handlers[('wf_api_stop_event')] = func

    ####### TODO: should this be simply on_prompt_event like the message is?

    def on_prompt(self, func):
        self.type_handlers[('wf_api_prompt_event')] = func

    def on_button(self, _func=None, *, button='*', taps='*'):
        def on_button_decorator(func):
            self.type_handlers[('wf_api_button_event', button, taps)] = func

        if _func:
            return on_button_decorator(_func)

        else:
            return on_button_decorator

    
    def on_notification(self, _func=None, *, name='*', event='*'):
        def on_notification_decorator(func):
            self.type_handlers[('wf_api_notification_event', name, event)] = func

        if _func:
            return on_notification_decorator(_func)

        else:
            return on_notification_decorator


    def on_timer(self, func):
        # unnamed timer
        self.type_handlers[('wf_api_timer_event')] = func

    ###### TODO: test all the ones from here down

    def on_timer_fired(self, func):
        # named timer
        self.type_handlers[('wf_api_timer_fired_event')] = func

    def on_speech(self, func):
        self.type_handlers[('wf_api_speech_event')] = func

    def on_progress(self, func):
        self.type_handlers[('wf_api_progress_event')] = func

    def on_play_inbox_message(self, func):
        self.type_handlers[('wf_api_play_inbox_message_event')] = func

    def on_call_connected(self, func):
        self.type_handlers[('wf_api_call_connected_event')] = func

    def on_call_disconnected(self, func):
        self.type_handlers[('wf_api_call_disconnected_event')] = func

    def on_call_failed(self, func):
        self.type_handlers[('wf_api_call_failed_event')] = func

    def on_call_received(self, func):
        self.type_handlers[('wf_api_call_received_event')] = func

    def on_call_ringing(self, func):
        self.type_handlers[('wf_api_call_ringing_event')] = func

    def on_call_start_request(self, func):
        self.type_handlers[('wf_api_call_start_request_event')] = func

    def on_call_progressing(self, func):
        self.type_handlers[('wf_api_call_progressing_event')] = func

    def on_sms(self, func):
        self.type_handlers[('wf_api_sms_event')] = func

    def on_incident(self, func):
        self.type_handlers[('wf_api_incident_event')] = func

    def on_interaction_lifecycle(self, func):
        self.type_handlers[('wf_api_interaction_lifecycle_event')] = func

    def on_resume(self, func):
        self.type_handlers[('wf_api_resume_event')] = func

    def get_handler(self, event:dict):
        t = event['_type']

        # assume no-arg handler; if not, check the handlers that require args
        # for args, check for handler registered with specific values first; if not, then check variations with wildcard values
        h = self.type_handlers.get((t), None)
        if not h:
            if t == 'wf_api_button_event':
                h = self.type_handlers.get((t, event['button'], event['taps']), None)
                if not h:
                    # prefer button match over taps
                    h = self.type_handlers.get((t, event['button'], '*'), None)
                    if not h:
                        h = self.type_handlers.get((t, '*', event['taps']), None)
                        if not h:
                            h = self.type_handlers.get((t, '*', '*'), None)

            elif t == 'wf_api_notification_event':
                h = self.type_handlers.get((t, event['name'], event['event']), None)
                if not h:
                    # prefer name match over event
                    h = self.type_handlers.get((t, event['name'], '*'), None)
                    if not h:
                        h = self.type_handlers.get((t, '*', event['event']), None)
                        if not h:
                            h = self.type_handlers.get((t, '*', '*'), None)

            elif t == 'wf_prompt_event':
                if event['type'] == 'started':
                    h = self.type_handlers.get(('wf_api_prompt_start_event'), None)
                elif event['type'] == 'stopped' or event['type'] == 'failed':
                    h = self.type_handlers.get(('wf_api_prompt_stop_event'), None)

        return h


class WorkflowException(Exception):
    def __init__(self, message:str):
        self.message = message
        super().__init__(self.message)


@singledispatch
def remove_null(obj):
    return obj

@remove_null.register(list)
def _process_list(l):
    return [remove_null(v) for v in l]

@remove_null.register(dict)
def _process_list(d):
    return {k:remove_null(v) for k,v in d.items() if v is not None}


class CustomAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f'[{self.extra["cid"]}] {msg}', kwargs


class Relay:
    """Includes the main functionalities that are used within workflows,
    such as functions for communicating with the device, sending out
    notifications to groups, handling workflow events, and performing physical actions
    on the device such as manipulating LEDs and creating vibrations.
    """
    def __init__(self, workflow:Workflow):
        """Initializes workflow fields.

        Args:
            workflow (Workflow): your workflow.
        """
        self.workflow = workflow
        self.websocket = None
        self.id_futures = {}  # {_id: future}
        self.event_futures = {}
        self.logger = None

    def get_cid(self):
        return f'{self.workflow.name}:{id(self.websocket)}'

    def fromJson(self, websocketMessage):
        dictMessage = json.loads(websocketMessage)
        return self.cleanIntArrays(dictMessage)

    def cleanIntArrays(self, dictMessage):
        # work around the JSON formatting issue in iBot
        # that gives us an array of ints instead of a string:
        # will be fixed in iBot 3.9 via PE-17571

        if isinstance(dictMessage, dict):
            for key in dictMessage.keys():
                if isinstance(dictMessage[key], (list, dict)):
                    dictMessage[key] = self.cleanIntArrays(dictMessage[key])
        elif isinstance(dictMessage, list):
            allInt = True;
            for item in dictMessage:
                if not isinstance(item, int):
                    allInt = False;
                    break;
            if allInt and (len(dictMessage) > 0):
                dictMessage = "".join(chr(i) for i in dictMessage)
        return dictMessage

    def make_target_uris(self, trigger:dict):
        """Creates a target URN after receiving a workflow trigger.

        Args:
            trigger (dict): workflow trigger.

        Raises:
            WorkflowException: thrown if the trigger param is not a dictionary.
            WorkflowException: thrown if the trigger param is not a trigger dictionary.
            WorkflowException: thrown if there is no source_uri definition in the trigger.

        Returns:
            a target object created from the trigger.
        """
        if not isinstance(trigger, dict):
            raise WorkflowException('trigger parameter is not a dictionary')
        if not 'args' in trigger:
            raise WorkflowException('trigger parameter is not a trigger dictionary')
        if not 'source_uri' in trigger['args']:
            raise WorkflowException('there is no source_uri definition in the trigger')
        target = {
            'uris': [ trigger['args']['source_uri'] ]
        }
        return target

    def targets_from_source_uri(self, source_uri:str):
        """Creates a target object from a source URN.
        Enables the device to perform the desired action after the function
        has been called.  Used interanlly by interaction functions such as
        say(), listen(), vibration(), etc.

        Args:
            source_uri (str): source uri that will be used to create a target.

        Returns:
            the target that was created from a source URN.
        """
        targets = {
            'uris': [ source_uri ]
        }
        return targets

    async def handle(self, websocket):
        """Handles websocket events by creating tasks based
        off o the type of event that was received.

        Args:
            websocket: the websocket event.
        """
        self.websocket = websocket
        self.logger = CustomAdapter(logger, {'cid': self.get_cid()})

        self.logger.info(f'workflow started from {self.websocket.path}')

        try:
            async for m in websocket:
                self.logger.debug(f'recv: {m}')
                e = self.fromJson(m)
                _id = e.get('_id', None)
                _type = e.get('_type', None)
                request_id = e.get('request_id', None)
    
                if _id:
                    fut = self.id_futures.pop(_id, None)
                    if fut:
                        fut.set_result(e)
                    else:
                        self.logger.warning(f'found response for unknown _id {_id}')

                else:
                    handled = False
                    future = self._pop_event_match(e)
                    if future:
                        future.set_result(e)
                        handled = True

                    # events that don't have an _id field (some events do have an _id field for async response data)
                    h = self.workflow.get_handler(e)
                    if h:
                        if _type == 'wf_api_start_event':
                            # logger.debug(f"handle start_event with trigger: {e['trigger']}")
                            asyncio.create_task(self.wrapper(h, e['trigger']))

                        elif _type == 'wf_api_stop_event':
                            # logger.debug(f"handle stop_event with reason: {e['reason']}")
                            asyncio.create_task(self.wrapper(h, e['reason']))
    
                        elif _type == 'wf_api_prompt_event':
                            type = e['type'] if 'type' in e else None
                            # logger.debug(f"handle prompt_start_event with source_uri: {e['source_uri']}, type: {e['type']}")
                            asyncio.create_task(self.wrapper(h, e['source_uri'], e['type']))
  
                        elif _type == 'wf_api_prompt_stop_event':
                            # logger.debug(f"handle prompt_stop_event with source_uri: {e['source_uri']}, id: {e['id']}")
                            asyncio.create_task(self.wrapper(h, e['source_uri']))
 

                        elif _type == 'wf_api_button_event':
                            # logger.debug(f"wf_api_button_event with button: {e['button']}, taps: {e['taps']}, source_uri: {e['source_uri']}")
                            asyncio.create_task(self.wrapper(h, e['button'], e['taps'], e['source_uri']))
    
                        elif _type == 'wf_api_notification_event':
                            # logger.debug(f"wf_api_notification_event with source_uri: {e['source_uri']}, name: {e['name']}, notification_state: {e['notification_state']}")
                            asyncio.create_task(self.wrapper(h, e['event'], e['name'], e['notification_state'], e['source_uri']))
    
                        elif _type == 'wf_api_timer_event':
                            # logger.debug(f"wf_api_timer_event")
                            asyncio.create_task(self.wrapper(h))

                        elif _type == 'wf_api_timer_fired_event':
                            # logger.debug(f"wf_api_timer_fired_event, name={e['name']}")
                            asyncio.create_task(self.wrapper(h, e['name']))

                        elif _type == 'wf_api_speech_event':
                            text = e['text'] if 'text' in e else None
                            audio = e['audio'] if 'audio' in e else None
                            # logger.debug(f"wf_api_speech_event: text: {text}, audio: {audio}, lang: {e['lang']}, request_id: {e['request_id']}, source_uri{e['source_uri']}")
                            asyncio.create_task(self.wrapper(h, text, audio, e['lang'], e['request_id'], e['source_uri']))

                        elif _type == 'wf_api_progress_event':
                            # logger.debug(f"wf_api_progress_event: _id: {_id}")
                            asyncio.create_task(self.wrapper(h))

                        elif _type == 'wf_api_play_inbox_message_event':
                            # logger.debug(f"wf_api_play_inbox_message_event with action: {e['action']}")
                            asyncio.create_task(self.wrapper(h, e['action']))

                        elif _type == 'wf_api_call_connected_event':
                            # logger.debug(f"wf_api_call_connected_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch'], e['connect_time_epoch']))

                        elif _type == 'wf_api_call_disconnected_event':
                            # logger.debug(f"wf_api_call_disconnected_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['reason'], e['start_time_epoch'], e['connect_time_epoch'], e['end_time_epoch']))

                        elif _type == 'wf_api_call_failed_event':
                            # logger.debug(f"wf_api_call_failed_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['reason'], e['start_time_epoch'], e['connect_time_epoch'], e['end_time_epoch']))
    
                        elif _type == 'wf_api_call_received_event':
                            # logger.debug(f"wf_api_call_received_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch']))
    
                        elif _type == 'wf_api_call_ringing_event':
                            # logger.debug(f"wf_api_call_ringing_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch']))
    
                        elif _type == 'wf_api_call_progressing_event':
                            # logger.debug(f"wf_api_call_progressing_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch'], e['connect_time_epoch']))
    
                        elif _type == 'wf_api_call_start_request_event':
                            # logger.debug(f"wf_api_call_start_request_event with uri: {e['uri']}")
                            asyncio.create_task(self.wrapper(h, e['uri']))
    
                        elif _type == 'wf_api_sms_event':
                            # logger.debug(f"wf_api_sms_event with id: {e['id']}, event: {e['event']}")
                            asyncio.create_task(self.wrapper(h, e['id'], e['event']))
    
                        elif _type == 'wf_api_incident_event':
                            # logger.debug(f"wf_api_incident_event with type: {e['type']}, id: {e['id']}, reason: {e['reason']}")
                            asyncio.create_task(self.wrapper(h, e['type'], e['id'], e['reason']))
    
                        elif _type == 'wf_api_interaction_lifecycle_event':
                            reason = e['reason'] if 'reason' in e else None

                            # logger.debug(f"wf_api_interaction_lifecycle_event with type: {e['type']}, source_uri: {e['source_uri']}, reason: {reason}")
                            asyncio.create_task(self.wrapper(h, e['type'], e['source_uri'], reason))
    
                        elif _type == 'wf_api_resume_event':
                            # logger.debug(f"wf_api_resume_event with trigger: {e['trigger']}")
                            asyncio.create_task(self.wrapper(h, e['trigger']))
    
                    elif not handled:
                        self.logger.warning(f'no handler found for _type {e["_type"]}')

        except websockets.exceptions.ConnectionClosedError:
            # ibot closes the connection on terminate(); this is expected
            pass

        except Exception as x:
            self.logger.error(f'{x}', exc_info=True)

        finally:
            self.logger.info('workflow terminated')

    # run handlers with exception logging; needed since we cannot await handlers
    async def wrapper(self, h, *args):
        """Runs handlers with exception logging.  Needed since we 
        cannot await handlers.

        Args:
            h: the handler.
        """
        try:
            await h(self, *args)
        except Exception as x:
            self.logger.error(f'{x}', exc_info=True)

    async def send(self, obj):
        _id = uuid.uuid4().hex
        obj['_id'] = _id

        # TODO: ibot add responses to all _request events? if so, await them here ... and check for error responses

        await self._send(json.dumps(obj))


    async def sendReceive(self, obj, uid=None):
        _id = uid if uid else uuid.uuid4().hex
        obj['_id'] = _id

        fut = asyncio.get_event_loop().create_future()
        self.id_futures[_id] = fut

        # TODO: ibot currently loads null as the string 'null'
        await self._send(json.dumps(remove_null(obj)))

        # wait on the response
        await fut

        rsp = fut.result()
        if rsp['_type'] == 'wf_api_error_response':
            raise WorkflowException(rsp['error'])

        return fut.result()


    async def _send(self, s):
        self.logger.debug(f'send: {s}')
        await self.websocket.send(s)


    async def get_var(self, name:str, default=None):
        """Retrieves a variable that was set either during workflow registration
        or through the set_var() function.  The variable can be retrieved anywhere
        within the workflow, but is erased after the workflow terminates.

        Args:
            name (str): name of the variable to be retrieved.
            default (optional): default value of the variable if it does not exist. Defaults to None.

        Returns:
            the variable requested.
        """
        ### TODO: look in self.workflow.state to see all of what is available
        event = {
            '_type': 'wf_api_get_var_request',
            'name': name
        }
        v = await self.sendReceive(event)
        return v.get('value', default)

    async def set_var(self, name:str, value:str):
        """Sets a variable with the corresponding name and value. Scope of
        the variable is from start to end of a workflow.
        Args:
            name (str): name of the variable to be created.
            value (str): value that the variable will hold.
        """
        event = {
            '_type': 'wf_api_set_var_request',
            'name': name,
            'value': value
        }
        response = await self.sendReceive(event)
        return response['value']

    async def unset_var(self, name:str):
        """Unsets the value of a variable.  

        Args:
            name (str): the name of the variable whose value you would like to unset.
        """
        event = {
            '_type': 'wf_api_unset_var_request',
            'name': name
        }
        await self.sendReceive(event)

    def interaction_options(color:str="0000ff", input_types:list=[], home_channel:str="suspend"):
        """Options for when an interaction is started via a workflow.

        Args:
            color (str, optional): desired color of LEDs when an interaction is started. Defaults to "0000ff".
            input_types (list, optional): input types you would like for the interaction. Defaults to [].
            home_channel (str, optional): home channel for the device during the interaction. Defaults to "suspend".

        Returns:
            the options specified.
        """
        options = {
            'color': color,
            'input_types': input_types,
            'home_channel': home_channel
        }
        return options

    async def start_interaction(self, target, name:str, options=None):
        """Starts an interaction with the user.  Triggers an INTERACTION_STARTED event
        and allows the user to interact with the device via functions that require an 
        interaction URN.

        Args:
            target (target): the device that you would like to start an interaction with.
            name (str): a name for your interaction.
            options (optional): can be color, home channel, or input types. Defaults to None.
        """
        event = {
            '_type': 'wf_api_start_interaction_request',
            '_target': target,
            'name': name,
            'options': options
        }
        await self.sendReceive(event)

    async def end_interaction(self, target, name: str):
        """Ends an interaction with the user.  Triggers an INTERACTION_ENDED event to signify
        that the user is done interacting with the device.

        Args:
            target(str): the device that you would like to end an interaction with.
            name (str): the name of the interaction that you would like to end.
        """
        event = {
            '_type': 'wf_api_end_interaction_request',
            '_target': self.targets_from_source_uri(target),
            'name': name
        }
        await self.sendReceive(event)

    def _set_event_match(self, criteria:dict):
        if not isinstance(criteria, dict):
            raise WorkflowException("criteria is not a dict")
        match_data = criteria.copy()
        uid = uuid.uuid4().hex
        future = asyncio.get_event_loop().create_future()
        match_data['_timestamp'] = time.time()
        match_data['_future'] = future
        self.event_futures[uid] = match_data
        return future

    def _pop_event_match(self, event):
        # check if event matches anything we are waiting for
        now = time.time()
        for uid in self.event_futures:
            # purge old items (30 minutes)
            age = now - self.event_futures[uid]['_timestamp']
            if age > 1800:
                self.event_futures.pop(uid, None)
                continue
            matches = True
            criteria = self.event_futures[uid]
            for key in criteria:
                if key == '_timestamp' or key == '_future':
                    continue
                # no criteria will match always
                if not key in event:
                    continue
                if self.event_futures[uid][key] != event[key]:
                    matches = False
                    break
            if matches:
                future = self.event_futures[uid]['_future']
                self.event_futures.pop(uid, None)
                return future
        return None

    async def _wait_for_event_match(self, future, timeout:int):
        await asyncio.wait_for(future, timeout)
        event = future.result()
        if event['_type'] == 'wf_api_error_response':
            raise WorkflowException(event['error'])
        return event

    async def listen(self, target, request_id, phrases=None, transcribe:bool=True, alt_lang:str=None, timeout:int=60,):
        """Listens for the user to speak into the device.  Utilizes speech to text functionality to interact
        with the user.

        Args:
            target (str): the interaction URN.
            request_id (str): the id of the workflow request.
            phrases (string[], optional): optional phrases that you would like to limit the user's response to. Defaults to None.
            transcribe (bool, optional): whether you would like to transcribe the user's reponse. Defaults to True.
            timeout (int, optional): timeout for how long the device will wait for user's response. Defaults to 60.
            alt_lang (str, optional): if you would like the device to listen for a response in a specific language. Defaults to None.

        Returns:
            text representation of what the user had spoken into the device.
        """
        if phrases is None:
            phrases = [ ]
        if isinstance(phrases, str):
            phrases = [ phrases ]

        _id = uuid.uuid4().hex
        event = {
            '_type': 'wf_api_listen_request',
            '_target': self.targets_from_source_uri(target),
            'request_id': request_id,
            'phrases': phrases,
            'transcribe': transcribe,
            'timeout': timeout,
            'alt_lang': alt_lang
        }

        criteria = {
            '_type': 'wf_api_speech_event',
            'request_id': _id
        }
        # need to add this before sendReceive to avoid race condition
        event_future = self._set_event_match(criteria)
        await self.sendReceive(event, _id)
        speech_event = await self._wait_for_event_match(event_future, timeout)

        if transcribe:
            return speech_event['text']
        else:
            return speech_event['audio']

    async def play(self, target, filename:str):
        """Plays a custom audio file that was uploaded by the user.

        Args:
            target(str): the interaction URN.
            filename (str): the name of the audio file.

        Returns:
            the response id after the audio file has been played on the device.
        """
        event = {
            '_type': 'wf_api_play_request',
            '_target': self.targets_from_source_uri(target),
            'filename': filename
        }
        response = await self.sendReceive(event)
        return response['id']

    async def play_and_wait(self, target, filename:str):
        """Plays a custom audio file that was uploaded by the user.
        Waits until the audio file has finished playing before continuing through
        the workflow.

        Args:
            target(str): the interaction URN.
            filename (str): the name of the audio file.

        Returns:
            the response id after the audio file has been played on the device.
        """
        _id = uuid.uuid4().hex
        event = {
            '_type': 'wf_api_play_request',
            '_target': self.targets_from_source_uri(target),
            'filename': filename
        }

        criteria = {
            '_type': 'wf_api_prompt_event',
            'type': 'stopped',
            'id': _id
        }

        event_future = self._set_event_match(criteria)
        response = await self.sendReceive(event, _id)
        await self._wait_for_event_match(event_future, 30)
        return response['id']

    async def say(self, target, text:str, lang:str='en-US'):
        """Utilizes text to speech capabilities to make the device 'speak' to the user.

        Args:
            target(str): the interaction URN.
            text (str): what you would like the device to say.
            lang (str, optional): the language of the text that is being spoken. Defaults to 'en-US'.

        Returns:
            the response ID after the device speaks to the user.
        """
        event = {
            '_type': 'wf_api_say_request',
            '_target': self.targets_from_source_uri(target),
            'text': text,
            'lang': lang
        }
        response = await self.sendReceive(event)
        return response['id']

    async def say_and_wait(self, target, text:str, lang:str='en-US'):
        """Utilizes text to speech capabilities to make the device 'speak' to the user.
        Waits until the text is fully played out on the device before continuing.

        Args:
            target(str): the interaction URN.
            text (str): what you would like the device to say.
            lang (str, optional): the language of the text that is being spoken. Defaults to 'en-US'.

        Returns:
            the response ID after the device speaks to the user.
        """
        _id = uuid.uuid4().hex
        event = {
            '_type': 'wf_api_say_request',
            '_target': self.targets_from_source_uri(target),
            'text': text,
            'lang': lang
        }

        criteria = {
            '_type': 'wf_api_prompt_event',
            'type': 'stopped',
            'id': _id }

        event_future = self._set_event_match(criteria)
        response = await self.sendReceive(event, _id)
        await self._wait_for_event_match(event_future, 30)
        logger.debug(f'wait complete for {target}')
        return response['id']

    # target properties: uri: array of string ids

    def push_options(self, priority:str='normal', title:str=None, body:str=None, sound:str='default'):
        """Push options for a virtual device after receiving a notification on the Relay App.

        Args:
            priority (str, optional): priority of the notification. Can be 'normal', 'high', or 'critical'. Defaults to 'normal'.
            title (str, optional): title of the notification. Defaults to None.
            body (str, optional): body of the notification. Defaults to None.
            sound (str, optional): sound to be played when notification appears on app. Can be 'default', or 'sos'.  Defaults to 'default'.

        Returns:
            the options for priority and sound as specified.
        """

        options = { 
            'priority': priority,
            'sound': sound
        }
        if title is not None:
            options['title'] = title
        if body is not None:
            options['body'] = body
        return options

    # repeating tone plus tts until button press
    async def alert(self, target, originator:str, name:str, text:str, push_options:dict={}):
        """Sends out an alert to the specified group of devices and the Relay Dash.

        Args:
            target(str): the group URN that you would like to send an alert to.
            originator (str): the URN of the device that triggered the alert.
            name (str): a name for your alert.
            text (str): the text that you would like to be spoken to the group as your alert.
            push_options (dict, optional): push options for if the alert is sent to the Relay app on a virtual device. Defaults to {}.
        """
        await self._send_notification(target, originator, 'alert', text, name, push_options)
    
    async def cancel_alert(self, target, name:str):
        """Cancels an alert that was sent to a group of devices.  Particularly useful if you would like to cancel the alert
        on all devices after one device has acknowledged the alert.

        Args:
            target(str): the device URN that has acknowledged the alert.
            name (str): the name of the alert.
        """
        await self._send_notification(target, None, 'cancel', None, name)

    async def broadcast(self, target, originator:str, name:str, text:str, push_options:dict={}):
        """Sends out a broadcasted message to a group of devices.  The message is played out on 
        all devices, as well as sent to the Relay Dash.

        Args:
            target(str): the group URN that you would like to broadcast your message to.
            originator (str): the device URN that triggered the broadcast.
            name (str): a name for your broadcast.
            text (str): the text that you would like to be broadcasted to your group.
            push_options (dict, optional): push options for if the broadcast is sent to the Relay app on a virtual device. Defaults to {}.
        """
        await self._send_notification(target, originator, 'broadcast', text, name, push_options)
    
    async def cancel_broadcast(self, target, name:str):
        """Cancels the broadcast that was sent to a group of devices.

        Args:
            target(str): the device URN that is cancelling the broadcast.
            name (str): the name of the broadcast that you would like to cancel.
        """
        await self._send_notification(target, None, 'cancel', None, name)

    async def notify(self, target, originator:str, name:str, text:str, push_options:dict={}):
        """Sends out a notification message to a group of devices.  

        Args:
            target(str): the group URN that you would like to notify.
            originator (str): the device URN that triggered the notification.
            name (str): a name for your notification.
            text (str): the text that you would like to be spoken out of the device as your notification.
            push_options (dict, optional): push options for if the notification is sent to the Relay app on a virtual device. Defaults to {}.
        """
        await self._send_notification(target, originator, 'notify', text, name, push_options)
    
    async def cancel_notify(self, target, name:str):
        """Cancels the notification that was sent to a group of devices.

        Args:
            target (str): the device URN that is cancelling the notification.
            name (str): the name of the notification that you would like to cancel.
        """
        await self._send_notification(target, None, 'cancel', None, name)

    async def _send_notification(self, target, originator:str, ntype:str, text:str, name:str, push_options:dict=None):
        """Used for sending a notification on the server.  Private method that is
        used by alert(), broadcast(), and notify().

        Args:
            target (str): the group URN that you are sending a notification to.
            originator (str): the device that triggered the notification.
            ntype (str): the type of notification, either 'alert', 'broadcast', or 'notify'.
            name (str): a name for your notification.
            text (str): the text of your notification.
            push_options (dict, optional): allows you to customize the push notification sent to a virtual device. Defaults to None.
        """
        event = {
            '_type': 'wf_api_notification_request',
            '_target': target,
            'originator': originator,
            'type': ntype,
            'name': name,
            'text': text,
            'target': target,
            'push_opts': push_options
        }
        await self.sendReceive(event)


    async def set_channel(self, target, channel_name:str, suppress_tts:bool=False, disable_home_channel:bool=False):
        """Sets the channel that a device is on.  This can be used to change the channel of a device during a workflow,
        where the channel will also be updated on the Relay Dash.

        Args:
            target (str): the device or interaction URN.
            channel_name (str): the name of the channel you would like to set your device to.
            suppress_tts (bool, optional): whether you would like to surpress text to speech. Defaults to False.
            disable_home_channel (bool, optional): whether you would like to disable the home channel. Defaults to False.
        """
        event = {
            '_type': 'wf_api_set_channel_request',
            '_target': self.targets_from_source_uri(target),
            'channel_name': channel_name,
            'suppress_tts': suppress_tts,
            'disable_home_channel': disable_home_channel
        }
        await self.sendReceive(event)


    async def get_device_name(self, target):
        """Returns the name of a targeted device.

        Args:
            target (str): the device or interaction URN.

        Returns:
            str: the name of the device.
        """
        v = await self._get_device_info(target, 'name')
        return v['name']

    async def get_device_address(self, target, refresh:bool=False):
        """Returns the address of a targeted device.

        Args:
            target (str): the device or interaction URN.
            refresh (bool, optional): whether you would like to refresh before retrieving the address. Defaults to False.

        Returns:
            str: the address of the device.
        """
        return await self.get_device_location(target, refresh)

    async def get_device_location(self, target, refresh:bool=False):
        """Returns the location of a targeted device.

        Args:
            target (str): the device or interaction URN.
            refresh (bool, optional): whether you would like to refresh before retrieving the location. Defaults to False.

        Returns:
            str: the location of the device.
        """
        v = await self._get_device_info(target, 'address', refresh)
        return v['address']

    async def get_device_latlong(self, target, refresh:bool=False):
        """Returns the latitude and longitude coordinates of a targeted device.

        Args:
            target (str): the device or interaction URN.
            refresh (bool, optional): whether you would like to refresh before retrieving the coordinates. Defaults to False.

        Returns:
            float[]: an array containing the latitude and longitude of the device.
        """
        v = await self._get_device_info(target, 'latlong', refresh)
        return v['latlong']

    async def get_device_indoor_location(self, target, refresh:bool=False):
        """Returns the indoor location of a targeted device.

        Args:
            target (str): the device or interaction URN.
            refresh (bool, optional): whether you would like to refresh before retrieving the location. Defaults to False.

        Returns:
            str: the indoor location of the device.
        """
        v = await self._get_device_info(target, 'indoor_location', refresh)
        return v['indoor_location']

    async def get_device_battery(self, target, refresh:bool=False):
        """Returns the battery of a targeted device.

        Args:
            target (str): the device or interaction URN.
            refresh (bool, optional): whether you would like to refresh before retrieving the battery. Defaults to False.

        Returns:
            int: the battery of the device.
        """
        v = await self._get_device_info(target, 'battery', refresh)
        return v['battery']

    async def get_device_type(self, target):
        """Returns the device type of a targeted device, i.e. gen 2, gen 3, etc.

        Args:
            target (str): the device or interaction URN.

        Returns:
            str: the device type.
        """
        v = await self._get_device_info(target, 'type')
        return v['type']
    
    async def get_device_id(self, target):
        """Returns the ID of a targeted device.

        Args:
            target (str): the device or interaction URN.

        Returns:
            str: the device ID.
        """
        v = await self._get_device_info(target, 'id')
        return v['id']

    #TODO: what does this actually do?
    async def get_user_profile(self, target):
        """Returns the user profile of a targeted device.

        Args:
            target (str): the device or interaction URN.

        Returns:
            str: the user profile registered to the device.
        """
        v = await self._get_device_info(target, 'username')
        return v['username']

    async def get_device_location_enabled(self, target):
        """Returns whether the location services on a device are enabled.

        Args:
            target (str): the device or interaction URN.

        Returns:
            str: 'true' if the device's location services are enabled, 'false' otherwise.
        """
        v = await self._get_device_info(target, 'location_enabled')
        return v['location_enabled']

    # target can have only one item
    async def _get_device_info(self, target, query, refresh:bool=False):
        """Used privately by device information functions to retrieve varying information
         on the device, such as the ID, location, battery, name and type.

        Args:
            target (str): the device or interaction URN.
            query (str): which category of information you are retrieving.
            refresh (bool): whether to refresh before retrieving information on the device.

        Returns:
            str: information on the device based on the query.
        """
        event = {
            '_type': 'wf_api_get_device_info_request',
            '_target': self.targets_from_source_uri(target),
            'query': query,
            'refresh': refresh
        }
        v = await self.sendReceive(event)
        return v


    async def set_device_name(self, target, name:str):
        """Sets the name of a targeted device and updates it on the Relay Dash.
        The name remains updated until it is set again via a workflow or updated manually
        on the Relay Dash.

        Args:
            target (str): the device or interaction URN.
            name (str): a new name for your device.
        """
        await self._set_device_info(target, 'label', name)

    async def set_device_channel(self, target, channel: str):
        """Sets the channel of a targeted device and updates it on the Relay Dash.
        The new channel remains until it is set again via a workflow or updated on the
        Relay Dash.

        Args:
            target (str): the device or interaction URN.
            channel (str): the channel that you would like to update your device to.
        """
        await self._set_device_info(target, 'channel', channel)

    async def enable_location(self, target):
        """Enables location services on a device.  Location services will remain
        enabled until they are disabled on the Relay Dash or through a workflow.

        Args:
            target (str): the device or interaction URN.
        """
        await self._set_device_info(target, 'location_enabled', 'true')
    
    async def disable_location(self, target):
        """Disables location services on a device.  Location services will remain
        disabled until they are enabled on the Relay Dash or through a workflow.

        Args:
            target (str): the device or interaction URN.
        """
        await self._set_device_info(target, 'location_enabled', 'false')

    async def _set_device_info(self, target, field, value):
        """Used privately by device information functions to set information
        fields on the device, such as the location, name, and channel of
        the device.

        Args:
            target (str): the device or interaction URN. This can only have one item.
            field (str): the type of information you would like to set, such as the 'name', 'channel', etc.
            value (str): the new value of the field.

        Returns:
            an event containing the updated device information.
        """
        event = {
            '_type': 'wf_api_set_device_info_request',
            '_target': self.targets_from_source_uri(target),
            'field': field,
            'value': value
        }
        v = await self.sendReceive(event)
        return event

    async def set_device_mode(self, target, mode:str='none'):
        """Sets the mode of the device.

        Args:
            target (str): the device or interaction URN.
            mode (str, optional): the updated mode of the device, which can be 'panic', 'alarm', or 'none'. Defaults to 'none'.
        """
        event = {
            '_type': 'wf_api_set_device_mode_request',
            'target': self.targets_from_source_uri(target),
            'mode': mode,
        }
        await self.sendReceive(event)

    def led_info(self, rotations:int=None, count:int=None, duration:int=None, repeat_delay:int=None, pattern_repeats=None, colors=None):
        """Sets information on a device, such as the number of rotations, count, duration, repeat delay, pattern repeats, 
        and colors.

        Args:
            rotations (int, optional): number of rotations. Defaults to None.
            count (int, optional): the number of times the LEDs will perform an action. Defaults to None.
            duration (int, optional): duration of the LED action in milliseconds. Defaults to None.
            repeat_delay (int, optional): the length of delay in milliseconds. Defaults to None.
            pattern_repeats (_type_, optional): the number of times a pattern should repeat. Defaults to None.
            colors (_type_, optional): hex-code of the color for the LEDs. Defaults to None.

        Returns:
            information field that was set on the LEDs.
        """
        info = { }
        if rotations is not None:
            info['rotations'] = rotations
        if count is not None:
            info['count'] = count
        if duration is not None:
            info['duration'] = duration
        if repeat_delay is not None:
            info['repeat_delay'] = repeat_delay
        if pattern_repeats is not None:
            info['pattern_repeats'] = pattern_repeats
        if colors is not None:
            info['colors'] = colors
        return info

    async def led_action(self, target, effect:str='flash', args=None):
        """Private method used for performing actions on the LEDs, such as creating 
        a rainbow, flashing, rotating, etc.

        Args:
            target (str): the interaction URN.
            effect (str, optional): effect to perform on LEDs, can be 'rainbow', 'rotate', 'flash', 'breath', 'static', or 'off'. Defaults to 'flash'.
            args (optional): use led_info() to create args. Defaults to None.
        """
        event = {
            '_type': 'wf_api_set_led_request',
            '_target': self.targets_from_source_uri(target),
            'effect': effect,
            'args': args
        }
        await self.sendReceive(event)

    async def switch_all_led_on(self, target, color:str='0000ff'):
        """Switches all of the LEDs on a device on to a specified color.

        Args:
            target (str): the interaction URN.
            color (str, optional): the hex color code you would like the LEDs to be. Defaults to '0000ff'.
        """
        await self.led_action(target, 'static', {'colors':{'ring': color}})

    async def switch_led_on(self, target, index:int, color:str='0000ff'):
        """Switches on an LED at a particular index to a specified color.

        Args:
            target (str): the interaction URN.
            index (int): the index of an LED, numbered 1-12.
            color (str, optional): the hex color code you would like to turn the LED to. Defaults to '0000ff'.
        """
        await self.led_action(target, 'static', {'colors':{index: color}})

    async def rainbow(self, target, rotations:int=-1):
        """Switches all of the LEDs on to a configured rainbow pattern and rotates the rainbow
        a specified number of times.

        Args:
            target (str): the interaction URN.
            rotations (int, optional): the number of times you would like the rainbow to rotate. Defaults to -1, meaning the 
            rainbow will rotate indefinitely.
        """
        await self.led_action(target, 'rainbow', {'rotations': rotations})

    async def flash(self, target, color:str='0000ff', count:int=-1):
        """Switches all of the LEDs on a device to a certain color and flashes them
        a specified number of times.

        Args:
            target (str): the interaction URN.
            color (str, optional): the hex color code you would like to turn the LEDs to. Defaults to '0000ff'.
            count (int, optional): the number of times you would like the LEDs to flash. Defaults to -1, meaning the LEDs
            will flash indefinitely.
        """
        await self.led_action(target, 'flash', {'colors': {'ring': color}, 'count': count})

    async def breathe(self, target, color:str='0000ff', count:int=-1):
        """Switches all of the LEDs on a device to a certain color and creates a 'breathing' effect, 
        where the LEDs will slowly light up a specified number of times.

        Args:
            target (str): the interaction URN.
            color (str, optional): the hex color code you would like to turn the LEDs to. Defaults to '0000ff'.
            count (int, optional): the number of times you would like the LEDs to 'breathe'. Defaults to -1, meaning
            the LEDs will 'breathe' indefinitely.
        """
        await self.led_action(target, 'breathe', {'colors': {'ring': color}, 'count': count})

    async def rotate(self, target, color:str='0000ff', rotations:int=-1):
        """Switches all of the LEDs on a device to a certain color and rotates them a specified number
        of times.

        Args:
            target (str): the interaction URN.
            color (str, optional): the hex color code you would like to turn the LEDs to. Defaults to '0000ff'.
            rotations (int, optional): the number of times you would like the LEDs to rotate. Defaults to -1, meaning
            the LEDs will rotate indefinitely.
        """
        await self.led_action(target, 'rotate', {'colors': {'1': color}, 'rotations': rotations})

    async def switch_all_led_off(self, target):
        """Switches all of the LEDs on a device off.

        Args:
            target (str): the interaction URN.
        """
        await self.led_action(target, 'off', {})


    async def vibrate(self, target, pattern:list=None):
        """Makes the device vibrate in a particular pattern.  You can specify
        how many vibrations you would like, the duration of each vibration in
        milliseconds, and how long you would like the pauses between each vibration to last
        in milliseconds.

        Args:
            target (str): the interaction URN.
            pattern (list, optional): an array representing the pattern of your vibration. Defaults to None.
        """
        if not pattern:
            pattern = [100, 500, 500, 500, 500, 500]

        event = {
            '_type': 'wf_api_vibrate_request',
            '_target': self.targets_from_source_uri(target),
            'pattern': pattern
        }
        await self.sendReceive(event)

    async def start_timer(self, timeout:int=60):
        """Starts an unnamed timer, meaning this will be the only timer on your device.
        The timer will stop when it reaches the limit of the 'timeout' parameter.

        Args:
            timeout (int): the number of seconds you would like to wait until the timer stops.
        """
        event = {
            '_type': 'wf_api_start_timer_request',
            'timeout': timeout
        }
        await self.sendReceive(event)

    async def stop_timer(self):
        """Stops an unnamed timer.
        """
        event = {
            '_type': 'wf_api_stop_timer_request'
        }
        await self.sendReceive(event)


    async def terminate(self):
        """Terminates a workflow.  This method is usually called
        after your workflow has completed and you would like to end the 
        workflow by calling end_interaction(), where you can then terminate
        the workflow.
        """
        event = {
            '_type': 'wf_api_terminate_request'
        }
        # there is no response
        await self.send(event)


    async def create_incident(self, originator, itype:str):
        """Creates an incident that will alert the Relay Dash.

        Args:
            originator (str): the device URN that triggered the incident.
            itype (str): the type of incident that occurred.

        Returns:
            str: the incident ID.
        """
        # TODO: what are the values for itype?
        event = {
            '_type': 'wf_api_create_incident_request',
            'type': itype,
            'originator_uri': originator
        }
        v = await self.sendReceive(event)
        return v['incident_id']

    async def resolve_incident(self, incident_id:str, reason:str):
        """Resolves an incident that was created.

        Args:
            incident_id (str): the ID of the incident you would like to resolve.
            reason (str): the reason for resolving the incident.
        """
        event = {
            '_type': 'wf_api_resolve_incident_request',
            'incident_id': incident_id,
            'reason': reason
        }
        await self.sendReceive(event)
    
    async def restart_device(self, target):
        """Restarts a device during a workflow, without having
        to physically restart the device via hodling down the '-' button.

        Args:
            target (str): the URN of the device you would like to restart.
        """

        event = {
            '_type': 'wf_api_device_power_off_request',
            '_target': self.targets_from_source_uri(target),
            'restart': True
        }
        await self.sendReceive(event)
    
    async def power_down_device(self, target):
        """Powers down a device during a workflow, without
        having to physically power down the device via holding down the '+' button.

        Args:
            target (str): the URN of the device that you would like to power down.
        """
        event = {
            '_type': 'wf_api_device_power_off_request',
            '_target': self.targets_from_source_uri(target),
            'restart': False
        }
        await self.sendReceive(event)
    
    async def stop_playback(self, target, id:str=None):
        event = None
        if type(id) == list:
            event = {
                '_type': 'wf_api_stop_playback_request',
                '_target': target,
                'ids': id
            }
        elif type(id) == str:
            id = [id]
            event = {
                '_type': 'wf_api_stop_playback_request',
                '_target': target,
                'ids': id
            }
        elif id is None:
            event = {
                '_type': 'wf_api_stop_playback_request',
                '_target': target
            }
        await self.sendReceive(event)

    async def translate(self, text:str, from_lang:str='en-US', to_lang:str='es-ES'):
        """Translates text from one language to another.

        Args:
            text (str): the text that you would like to translate.
            from_lang (str): the language that you would like to translate from.
            to_lang (str): the language that you would like to translate to.

        Returns:
            str: the translated text.
        """
        event = {
            '_type': 'wf_api_translate_request',
            'text': text,
            'from_lang': from_lang,
            'to_lang': to_lang
        }
        response = await self.sendReceive(event)
        return response['text']

    # target can have only one item
    async def place_call(self, target, uri:str):
        event = {
            '_type': 'wf_api_call_request',
            '_target': target,
            'uri': uri
        }
        response = await self.sendReceive(event)
        return response['call_id']

    # target can have only one item
    async def answer_call(self, target, call_id:str):
        event = {
            '_type': 'wf_api_answer_request',
            '_target': target,
            'call_id': call_id
        }
        await self.sendReceive(event)
    
    # target can have only one item
    async def hangup_call(self, target, call_id:str):
        event = {
            '_type': 'wf_api_hangup_request',
            '_target': target,
            'call_id': call_id
        }
        await self.sendReceive(event)

    ##### TODO: test me from this point down

    async def get_group_members(self, group_uri:str):
        """Returns the members of a particular group.

        Args:
            group_uri (str): the URN of the group that you would like to retrieve members from.

        Returns:
            str[]: a list of the members within the specified group.
        """
        event = {
            '_type': 'wf_api_group_query_request',
            'query': 'list_members',
            'group_uri': group_uri
        }
        response = await self.sendReceive(event)
        return response['member_uris']

    async def is_group_member(self, group_name_uri:str, potential_member_name_uri:str):
        """Checks whether a device is a member of a particular group.

        Args:
            group_uri (str): the URN of a group.
            potential_member_name_uri: the URN of the device name.

        Returns:
            str: 'true' if the device is a member of the specified group, 'false' otherwise.
        """
        group_name = parse_group_name(group_name_uri)
        device_name = parse_device_name(potential_member_name_uri)
        group_uri = group_member(group_name, device_name)
        event = {
            '_type': 'wf_api_group_query_request',
            'query': 'is_member',
            'group_uri': group_uri
        }
        response = await self.sendReceive(event)
        return response['is_member']   

    # target can have only one item
    async def set_user_profile(self, target:str, username:str, force:bool=False):
        """Sets the profile of a user by updating the username.

        Args:
            target (str): the device URN whose profile you would like to update.
            username (str): the updated username for the device.
            force (bool, optional): whether you would like to force this update. Defaults to False.
        """
        event = {
            '_type': 'wf_api_set_user_profile_request',
            '_target': self.targets_from_source_uri(target),
            'username': username,
            'force': force
        }
        await self.sendReceive(event)

    # target can have only one item
    async def get_unread_inbox_size(self, target):
        """Retrieves the number of messages in a device's inbox.

        Args:
            target (str): the device or interaction URN whose inbox you would like to check.

        Returns:
            str: the number of messages in the specified device's inbox.
        """
        event = {
            '_type': 'wf_api_inbox_count_request',
            '_target': self.targets_from_source_uri(target)
        }
        response = await self.sendReceive(event)
        return response['count']

    async def play_unread_inbox_messages(self, target):
        """Play a targeted device's inbox messages.

        Args:
            target (str): the device or interaction URN whose inbox messages you would like to play.
        """
        event = {
            '_type': 'wf_api_play_inbox_messages_request',
            '_target': self.targets_from_source_uri(target)
        }
        await self.sendReceive(event)

    async def log_message(self, message:str, category:str='default'):
        """Log an analytics event from a workflow with the specified content and
        under a specified category. This does not log the device who
        triggered the workflow that called this function.

        Args:
            message (str): a description for your analytical event.
            category (str): a category for your analytical event.
        """
        event = {
            '_type': 'wf_api_log_analytics_event_request',
            'content': message,
            'content_type': 'text/plain',
            'category': category
        }
        await self.sendReceive(event)

    async def log_user_message(self, message:str, target, category:str):
        """Log an analytic event from a workflow with the specified content and
        under a specified category.  This includes the device who triggered the workflow
        that called this function.

        Args:
            message (str): a description for your analytical event.
            target (str, optional): the URN of a the device that triggered this function. Defaults to None.
            category (str): a category for your analytical event.
        """
        event = {
            '_type': 'wf_api_log_analytics_event_request',
            'content': message,
            'content_type': 'text/plain',
            'category': category,
            'device_uri': target
        }
        await self.sendReceive(event)

    async def set_timer(self,  timer_type:str='timeout', name:str, timeout:int=60, timeout_type:str='secs'):
        """ Serves as a named timer that can be either interval or timeout.  Allows you to specify
        the unit of time.

        Args:
            timer_type (str, optional): can be 'timeout' or 'interval'. Defaults to 'timeout'.
            name (str): a name for your timer.
            timeout (int): an integer representing when you would like your timer to stop.
            timeout_type (str, optional): can be 'ms', 'secs', 'mins' or 'hrs'. Defaults to 'secs'.
        """
        event = {
            '_type': 'wf_api_set_timer_request',
            'type': timer_type,
            'name': name,
            'timeout': timeout,
            'timeout_type': timeout_type
        }
        await self.sendReceive(event)

    async def clear_timer(self, name:str):
        """Clears the specified timer.

        Args:
            name (str): the name of the timer that you would like to clear.
        """
        event = {
            '_type': 'wf_api_clear_timer_request',
            'name': name
        }
        await self.sendReceive(event)

    async def sms(self, stype:str, text:str, uri:str):
        event = {
            '_type': 'wf_api_sms_request',
            'type': stype,
            'text': text,
            'uri': uri
        }
        response = await self.sendReceive(event)
        return response['message_id']

    async def enable_home_channel(self, target):
        await self._set_home_channel_state(target, True)
    
    async def disable_home_channel(self, target):
        await self._set_home_channel_state(target, False)

    async def _set_home_channel_state(self, target, enabled:bool=True):
        event = {
            '_type': 'wf_api_set_home_channel_state_request',
            '_target': self.targets_from_source_uri(target),
            'enabled': enabled
        }
        await self.sendReceive(event)

    # target can have only one item
    async def register(self, target, uri:str, password:str, expires:int):
        event = {
            '_type': 'wf_api_register_request',
            '_target': target,
            'uri': uri,
            'password': password,
            'expires': expires
        }
        await self.sendReceive(event)

    ############ the ones below here are just for testing error handling

    async def invalid_type(self):
        event = {
            '_type': 'wf_api_mkinard_breakage',
            'device_id': 'TheQuickBrownFoxJumpedOverTheLazyDog',
            'call_id': 'you can\'t catch me'
        }
        await self.sendReceive(event)

    async def missing_type(self):
        event = {
            'device_id': 'NowIsTheTimeForAllGoodMenToComeToTheAidOfYourCountry',
            'call_id': 'you can\'t catch me'
        }
        await self.sendReceive(event)


def __update_access_token(refresh_token:str, client_id:str):
    grant_url = f'https://{auth_hostname}/oauth2/token'
    grant_headers = {
        'User-Agent': version
    }
    grant_payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id
    }
    grant_response = requests.post(grant_url, headers=grant_headers, data=grant_payload, timeout=10.0)
    if grant_response.status_code != 200:
        raise WorkflowException(f"unable to get access_token: {grant_response.status_code}")
    grant_response_dict = grant_response.json()
    access_token = grant_response_dict['access_token']
    return access_token


def send_http_trigger(access_token:str, refresh_token:str, client_id:str, workflow_id:str, subscriber_id:str, user_id:str, action_args:dict=None):
    """A convenience method for sending an HTTP trigger to the Relay server.

    This generally would be used in a third-party system to start a Relay
    workflow via an HTTP trigger and optionally pass data to it with
    action_args.  Under the covers, this uses Python's "request" library
    for using the https protocol.

    If the access_token has expired and the request gets a 401 response,
    a new access_token will be automatically generated via the refresh_token,
    and the request will be resubmitted with the new access_token. Otherwise
    the refresh token won't be used.

    This method will return a tuple of (requests.Response, access_token)
    where you can inspect the http response, and get the updated access_token
    if it was updated (otherwise the original access_token will be returned).

    Args:
        access_token(str): the current access token. Can be a placeholder value
        and this method will generate a new one and return it. If the
        original value of the access token passed in here has expired,
        this method will also generate a new one and return it.

        refresh_token(str): the permanent refresh_token that can be used to
        obtain a new access_token. The caller should treat the refresh
        token as very sensitive data, and secure it appropriately.

        client_id(str): the auth_sdk_id as returned from "relay env".

        workflow_id(str): the workflow_id as returned from "relay workflow list".
        Usually starts with "wf_".

        subscriber_id(str): the subcriber UUID as returned from "relay whoami".

        user_id(str): the IMEI of the target device, such as 990007560023456.

        action_args (optional): a dict of any key/value arguments you want
        to pass in to the workflow that gets started by this trigger.
    """

    url = f'https://{server_hostname}/ibot/workflow/{workflow_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': version
    }
    query_params = {
        'subscriber_id': subscriber_id,
        'user_id': user_id
    }
    payload = {"action": "invoke"}
    if action_args:
        payload['action_args'] = action_args
    response = requests.post(url, headers=headers, params=query_params, json=payload, timeout=10.0)
    # check if access token expired, and if so get a new one from the refresh_token, and resubmit
    if response.status_code == 401:
        logger.debug(f'got 401 on workflow trigger, trying to get new access token')
        access_token = __update_access_token(refresh_token, client_id)
        headers['Authorization'] = f'Bearer {access_token}'
        response = requests.post(url, headers=headers, params=query_params, json=payload, timeout=10.0)
    logger.debug(f'workflow trigger status code={response.status_code}')
    return (response, access_token)


def get_device_info(access_token:str, refresh_token:str, client_id:str, subscriber_id:str, user_id:str):
    """A convenience method for getting all the details of a device.

    This will return quite a bit of data regarding device configuration and
    state. The result, if the query was successful, should have a large JSON
    dictionary.

    Args:
        access_token(str): the current access token. Can be a placeholder value
        and this method will generate a new one and return it. If the
        original value of the access token passed in here has expired,
        this method will also generate a new one and return it.

        refresh_token(str): the permanent refresh_token that can be used to
        obtain a new access_token. The caller should treat the refresh
        token as very sensitive data, and secure it appropriately.

        client_id(str): the auth_sdk_id as returned from "relay env".

        subscriber_id(str): the subcriber UUID as returned from "relay whoami".

        user_id(str): the IMEI of the target device, such as 990007560023456.
    """
    url = f'https://{server_hostname}/relaypro/api/v1/device/{user_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': version
    }
    query_params = { 'subscriber_id': subscriber_id }
    response = requests.get(url, headers=headers, params=query_params, timeout=10.0)
    if response.status_code == 401:
        logger.debug(f'got 401 on get, trying to get new access token')
        access_token = __update_access_token(refresh_token, client_id)
        headers['Authorization'] = f'Bearer {access_token}'
        response = requests.post(url, headers=headers, params=query_params, timeout=10.0)
    logger.debug(f'device_info status code={response.status_code}')
    return (response, access_token)

######## end of SDK
