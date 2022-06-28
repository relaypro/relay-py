
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
    """
    Class used for initializing the host and port in which the workflow will run,
    registering the workflow on a path, handling an ssl protocol, and then listening
    for a workflow trigger.
    """
    def __init__(self, host:str, port:int, **kwargs):
        """
        Function for initializing the host and port, and
        checking ssl

        Args:
            host (str): host for the workflow
            port (int): the port to listen for a trigger
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
        """
        Registers a workflow on the path

        Args:
            workflow (_type_): the workflow to be registered
            path (str): the path on which the workflow will be registered

        Raises:
            ServerException: thrown when a workflow is already registered on that path
        """
        if path in self.workflows:
            raise ServerException(f'a workflow is already registered at path {path}')
        self.workflows[path] = workflow

    def start(self):
        """
        Starts the ssl protocol and then listens on the server for a workflow trigger

        Raises:
            ServerException: thrown when the ssl_cert_file cannot be read
            ServerException: thrown when the ssl_key_file cannot be read
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
        """
        Handles a request on a path

        Args:
            websocket (_type_): websocket protocol
            path (str): path that contained the request
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

# Helper methods for creating and parsing out a URI

SCHEME = 'urn'
ROOT = 'relay-resource'
GROUP = 'group'
ID = 'id'
NAME = 'name'
DEVICE = 'device'
DEVICE_PATTERN = '?device='
INTERACTION_URI_NAME = 'urn:relay-resource:name:interaction'
INTERACTION_URI_ID = 'urn:relay-resource:id:interaction'

def construct(resource_type:str, id_type:str, id_or_name:str): 
    return f'{SCHEME}:{ROOT}:{id_type}:{resource_type}:{id_or_name}'

def group_id(id:str):
    return construct(GROUP, ID, urllib.parse.quote(id))

def group_name(name:str):
    return construct(GROUP, NAME, urllib.parse.quote(name))

def device_name(name:str):
    return construct(DEVICE, NAME, urllib.parse.quote(name))

def group_member(group:str, device:str):
    return f'{SCHEME}:{ROOT}:{NAME}:{GROUP}:{urllib.parse.quote(group)}{DEVICE_PATTERN}' + urllib.parse.quote(f'{SCHEME}:{ROOT}:{NAME}:{DEVICE}:{device}')

def device_id(id:str):
    return construct(DEVICE, ID, urllib.parse.quote(id))

def parse_group_name(uri:str):
    scheme, root, id_type, resource_type, name = urllib.parse.unquote(uri).split(':')
    if id_type == NAME and resource_type == GROUP:
        return name
    logger.error('invalid group urn')
    
def parse_group_id(uri:str):
    scheme, root, id_type, resource_type, id = urllib.parse.unquote(uri).split(':')
    if id_type == ID and resource_type == GROUP:
        return id
    logger.error('invalid group urn')

def parse_device_name(uri:str):
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
    uri = urllib.parse.unquote(uri)
    if is_interaction_uri(uri):
        scheme, root, id_type, resource_type, i_name, i_root, i_id_type, i_resource_type, name = uri.split(':')
        interaction_name, discard = i_name.split('?') 
        return interaction_name
    logger.error('not an interaction urn')

def is_interaction_uri(uri:str):
    if INTERACTION_URI_NAME in uri or INTERACTION_URI_ID in uri:
        return True
    return False

def is_relay_uri(uri:str):
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
    """
    Includes the main functionalities that are used within the workflows,
    including functions for communicating with the device, sending out
    notifications to groups, handling workflow events, and performing actions
    on the device like manipulating LEDs and creating vibrationss.
    """
    def __init__(self, workflow:Workflow):
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
        """
        Creates a target object after it receives a trigger in on_start_handler


        Args:
            trigger (dict): trigger that started the workflow.

        Raises:
            WorkflowException: thrown if the trigger param is not a dictionary.
            WorkflowException: thrown if the trigger param is not a trigger dictionary.
            WorkflowException: thrown if there is no source_uri definition in the trigger.

        Returns:
            _type_: a target object created from the trigger.
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
        """
        Creates a target from a source uri

        Args:
            source_uri (str): source uri that will be used to create a target

        Returns:
            _type_: the targets that were created from the uri
        """
        targets = {
            'uris': [ source_uri ]
        }
        return targets

    async def handle(self, websocket):
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
        """
        Retrieves a variable that was set either when registering a workflow
        or through the set_var() function

        Args:
            name (str): name of the variable to be retrieved.
            default (_type_, optional): default value of the variable if it does
            not exist. Defaults to None.

        Returns:
            _type_: the variable that was requested.
        """
        ### TODO: look in self.workflow.state to see all of what is available
        event = {
            '_type': 'wf_api_get_var_request',
            'name': name
        }
        v = await self.sendReceive(event)
        return v.get('value', default)

    async def set_var(self, name:str, value:str):
        """
        Sets a variable with the name and value passed in as parameters

        Args:
            name (str): name of the variable to be created
            value (str): value that the variable will hold
        """
        event = {
            '_type': 'wf_api_set_var_request',
            'name': name,
            'value': value
        }
        response = await self.sendReceive(event)
        return response['value']

    async def unset_var(self, name:str):
        """
        Unsets the value of a variable

        Args:
            name (str): the name of the variable whose value you would like to unset
        """
        event = {
            '_type': 'wf_api_unset_var_request',
            'name': name
        }
        await self.sendReceive(event)

    def interaction_options(color:str="0000ff", input_types:list=[], home_channel:str="suspend"):
        options = {
            'color': color,
            'input_types': input_types,
            'home_channel': home_channel
        }
        return options

    async def start_interaction(self, target, name:str, options=None):
        """
        Start an interaction with the user.

        Args:
            target (_type_): the device in which you would like to start an interaction with
            name (str): a name for your interaction.
            options (_type_, optional): options that you would like to pass in to your interaction. Defaults to None.
        """
        event = {
            '_type': 'wf_api_start_interaction_request',
            '_target': target,
            'name': name,
            'options': options
        }
        await self.sendReceive(event)

    async def end_interaction(self, target, name: str):
        """
        End an interaction with the user.

        Args:
            target (_type_): the device in which you would like to end the interaction.
            name (str): the name of the interaction that you would like to end.
        """
        event = {
            '_type': 'wf_api_end_interaction_request',
            '_target': target,
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

    async def listen(self, target, request_id, phrases=None, transcribe:bool=True, timeout:int=60, alt_lang:str=None):
        """
        Listens for the user to speak into the device.

        Args:
            target (_type_): the device that will listen to the user.
            request_id (_type_): the id of the workflow request
            phrases (_type_, optional): optional phrases that you would like to limit the user's response to. Defaults to None.
            transcribe (bool, optional): whether you would like to transcribe the user's reponse. Defaults to True.
            timeout (int, optional): timeout for how long the device will wait for user's response. Defaults to 60.
            alt_lang (str, optional): if you would like the device to listen for a response in another language. Defaults to None.

        Returns:
            _type_: text representation of what the user had spoken into the device.
        """
        if phrases is None:
            phrases = [ ]
        if isinstance(phrases, str):
            phrases = [ phrases ]

        _id = uuid.uuid4().hex
        event = {
            '_type': 'wf_api_listen_request',
            '_target': target,
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
        event = {
            '_type': 'wf_api_play_request',
            '_target': target,
            'filename': filename
        }
        response = await self.sendReceive(event)
        return response['id']

    async def play_and_wait(self, target, filename:str):
        _id = uuid.uuid4().hex
        event = {
            '_type': 'wf_api_play_request',
            '_target': target,
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
        # target must be an interaction URI, not a device URI
        event = {
            '_type': 'wf_api_say_request',
            '_target': target,
            'text': text,
            'lang': lang
        }
        response = await self.sendReceive(event)
        return response['id']

    async def say_and_wait(self, target, text:str, lang:str='en-US'):
        # target must be an interaction URI, not a device URI
        _id = uuid.uuid4().hex
        event = {
            '_type': 'wf_api_say_request',
            '_target': target,
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
        # values for priority: "normal", "high", "critical"
        # values for sound: "default", "sos"
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
    async def alert(self, target, originator:str, text:str, name:str, push_options:dict={}):
        await self._send_notification(target, originator, 'alert', name, text, None, push_options)
    
    async def cancel_alert(self, target, name:str, targets:dict=None):
        await self._send_notification(target, None, 'cancel', name, None, targets, None)

    # tone plus tts
    async def broadcast(self, target, originator:str, text:str, name:str, push_options:dict={}):
        await self._send_notification(target, originator, 'broadcast', name, text, push_options)
    
    async def cancel_broadcast(self, target, name:str, targets:dict=None):
        await self._send_notification(target, None, 'cancel', name, None, targets, None)

    # tone only
    async def notify(self, target, originator:str, text:str, name:str, push_options:dict={}):
        await self._send_notification(target, originator, 'notify', name, text, None, push_options)
    
    async def cancel_notification(self, target, name:str, targets:dict=None):
        await self._send_notification(target, None, 'cancel', name, None, targets, None)

    # text is used for creating an "ibot" notification. push_opts allows the developer to customize the push notification sent to a virtual device receiving the created notification

    async def _send_notification(self, target, originator:str, ntype:str, name:str, text:str, push_options:dict=None):
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
        event = {
            '_type': 'wf_api_set_channel_request',
            '_target': target,
            'channel_name': channel_name,
            'suppress_tts': suppress_tts,
            'disable_home_channel': disable_home_channel
        }
        await self.sendReceive(event)


    async def get_device_name(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'name', refresh)
        return v['name']

    async def get_device_address(self, target, refresh:bool=False):
        return await self.get_device_location(target, refresh)

    async def get_device_location(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'address', refresh)
        return v['address']

    async def get_device_latlong(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'latlong', refresh)
        return v['latlong']

    async def get_device_indoor_location(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'indoor_location', refresh)
        return v['indoor_location']

    async def get_device_battery(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'battery', refresh)
        return v['battery']

    async def get_device_type(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'type', refresh)
        return v['type']
    
    async def get_device_id(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'id', refresh)
        return v['id']

    async def get_user_profile(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'username', refresh)
        return v['username']

    async def get_device_location_enabled(self, target, refresh:bool=False):
        v = await self._get_device_info(target, 'location_enabled', refresh)
        return v['location_enabled']

    # target can have only one item
    async def _get_device_info(self, target, query, refresh:bool):
        event = {
            '_type': 'wf_api_get_device_info_request',
            '_target': target,
            'query': query,
            'refresh': refresh
        }
        v = await self.sendReceive(event)
        return v


    async def set_device_name(self, target, name:str):
        await self._set_device_info(target, 'label', name)

    async def set_device_channel(self, target, channel: str):
        await self._set_device_info(target, 'channel', channel)

    async def enable_location(self, target):
        await self._set_device_info(target, 'location_enabled', 'true')
    
    async def disable_location(self, target):
        await self._set_device_info(target, 'location_enabled', 'false')

    async def set_device_location_enabled(self, target, location_enabled: str):
        await self._set_device_info(target, 'location_enabled', channel)

    # target can have only one item
    async def _set_device_info(self, target, field, value):
        event = {
            '_type': 'wf_api_set_device_info_request',
            '_target': target,
            'field': field,
            'value': value
        }
        v = await self.sendReceive(event)
        return event

    async def set_device_mode(self, target, mode:str='none'):
        # values for mode: "panic", "alarm", "none"
        event = {
            '_type': 'wf_api_set_device_mode_request',
            'target': target,
            'mode': mode,
        }
        await self.sendReceive(event)

    def led_info(self, rotations:int=None, count:int=None, duration:int=None, repeat_delay:int=None, pattern_repeats=None, colors=None):
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

    async def led_action(self, target, effect:str="flash", args=None):
        # effect possible values: "rainbow", "rotate", "flash", "breathe", "static", "off"
        # use led_info to create args
        event = {
            '_type': 'wf_api_set_led_request',
            '_target': target,
            'effect': effect,
            'args': args
        }
        await self.sendReceive(event)

    # convenience functions
    async def switch_all_led_on(self, target, color:str='0000ff'):
        await self.set_led(target, 'static', {'colors':{'ring': color}})

    async def switch_led_on(self, target, index:int, color:str='0000ff'):
        await self.set_led(target, 'static', {'colors':{index: color}})

    async def rainbow(self, target, rotations:int=-1):
        await self.set_led(target, 'rainbow', {'rotations': rotations})

    async def flash(self, target, color:str='0000ff', count:int=-1):
        await self.set_led(target, 'flash', {'colors': {'ring': color}, 'count': count})

    async def breathe(self, target, color:str='0000ff', count:int=-1):
        await self.set_led(target, 'breathe', {'colors': {'ring': color}, 'count': count})

    async def rotate(self, target, color:str='0000ff', rotations:int=-1):
        await self.set_led(target, 'rotate', {'colors': {'1': color}, 'rotations': rotations})

    async def switch_all_led_off(self, target):
        await self.set_led(target, 'off', {})


    async def vibrate(self, target, pattern:list=None):
        if not pattern:
            pattern = [100, 500, 500, 500, 500, 500]

        event = {
            '_type': 'wf_api_vibrate_request',
            '_target': target,
            'pattern': pattern
        }
        await self.sendReceive(event)

    # unnamed timer
    async def start_timer(self, timeout:int):
        event = {
            '_type': 'wf_api_start_timer_request',
            'timeout': timeout
        }
        await self.sendReceive(event)

    # unnamed timer
    async def stop_timer(self):
        event = {
            '_type': 'wf_api_stop_timer_request'
        }
        await self.sendReceive(event)


    async def terminate(self):
        event = {
            '_type': 'wf_api_terminate_request'
        }
        # there is no response
        await self.send(event)


    async def create_incident(self, originator, itype:str):
        # TODO: what are the values for itype?
        event = {
            '_type': 'wf_api_create_incident_request',
            'type': itype,
            'originator_uri': originator
        }
        v = await self.sendReceive(event)
        return v['incident_id']

    async def resolve_incident(self, incident_id:str, reason:str):
        event = {
            '_type': 'wf_api_resolve_incident_request',
            'incident_id': incident_id,
            'reason': reason
        }
        await self.sendReceive(event)
    
    async def restart_device(self, target):
        event = {
            '_type': 'wf_api_device_power_off_request',
            '_target': target,
            'restart': True
        }
        await self.sendReceive(event)
    
    async def power_down_device(self, target):
        event = {
            '_type': 'wf_api_device_power_off_request',
            '_target': target,
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

    async def translate(self, text:str, from_lang:str, to_lang:str):
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
        event = {
            '_type': 'wf_api_group_query_request',
            'query': 'list_members',
            'group_uri': group_uri
        }
        response = await self.sendReceive(event)
        return response['member_uris']

    async def is_group_member(self, group_uri:str):
        event = {
            '_type': 'wf_api_group_query_request',
            'query': 'is_member',
            'group_uri': group_uri
        }
        response = await self.sendReceive(event)
        return response['is_member']   

    # target can have only one item
    async def set_user_profile(self, target:str, username:str, force:bool=False):
        event = {
            '_type': 'wf_api_set_user_profile_request',
            '_target': target,
            'username': username,
            'force': force
        }
        await self.sendReceive(event)

    # target can have only one item
    async def get_inbox_count(self, target):
        event = {
            '_type': 'wf_api_inbox_count_request',
            '_target': target
        }
        response = await self.sendReceive(event)
        return response['count']

    async def play_inbox_messages(self, target):
        event = {
            '_type': 'wf_api_play_inbox_messages_request',
            '_target': target
        }
        await self.sendReceive(event)

    async def log_message(self, content:str, category:str):
        event = {
            '_type': 'wf_api_log_analytics_event_request',
            'content': content,
            'content_type': 'text/plain',
            'category': category
        }
        await self.sendReceive(event)

    async def log_user_message(self, content:str, category:str, device_uri:str=None):
        event = {
            '_type': 'wf_api_log_analytics_event_request',
            'content': content,
            'content_type': 'text/plain',
            'category': category,
            'device_uri': device_uri
        }
        await self.sendReceive(event)

    # named timer
    # type can be 'timeout' or 'interval'
    # timeout_type can be 'ms', 'secs', 'mins', 'hrs'
    async def set_timer(self, name:str, timeout:int, timeout_type:str='secs', timer_type:str='timeout'):
        event = {
            '_type': 'wf_api_set_timer_request',
            'type': timer_type,
            'name': name,
            'timeout': timeout,
            'timeout_type': timeout_type
        }
        await self.sendReceive(event)

    # named timer
    async def clear_timer(self, name:str):
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
            '_target': target,
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

        access_token: the current access token. Can be a placeholder value
        and this method will generate a new one and return it. If the
        original value of the access token passed in here has expired,
        this method will also generate a new one and return it.

        refresh_token: the permanent refresh_token that can be used to
        obtain a new access_token. The caller should treat the refresh
        token as very sensitive data, and secure it appropriately.

        client_id: the auth_sdk_id as returned from "relay env".

        workflow_id: the workflow_id as returned from "relay workflow list".
        Usually starts with "wf_".

        subscriber_id: the subcriber UUID as returned from "relay whoami".

        user_id: the IMEI of the target device, such as 990007560023456.

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

        access_token: the current access token. Can be a placeholder value
        and this method will generate a new one and return it. If the
        original value of the access token passed in here has expired,
        this method will also generate a new one and return it.

        refresh_token: the permanent refresh_token that can be used to
        obtain a new access_token. The caller should treat the refresh
        token as very sensitive data, and secure it appropriately.

        client_id: the auth_sdk_id as returned from "relay env".

        subscriber_id: the subcriber UUID as returned from "relay whoami".

        user_id: the IMEI of the target device, such as 990007560023456.
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
