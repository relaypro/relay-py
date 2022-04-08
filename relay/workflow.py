import asyncio
import json
import logging
import time
import uuid
import websockets
import sys
import ssl

from functools import singledispatch

logging.basicConfig(format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# without a specific handler, it will log to the console. Uncomment below to not send to console.
# logger.addHandler(logging.NullHandler())
use_ssl = True
ssl_key_filename = '/etc/letsencrypt/live/myhost.mydomain.com/privkey.pem'
ssl_cert_filename = '/etc/letsencrypt/live/myhost.mydomain.com/fullchain.pem'

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.workflows = {}   # {path: workflow}

    def register(self, workflow, path):
        if path in self.workflows:
            raise ServerException(f'a workflow is already registered at path {path}')
        self.workflows[path] = workflow

    def start(self):
        ws_logger = logging.getLogger('websockets.server')
        ws_logger.setLevel(logging.DEBUG)

        if use_ssl:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(ssl_cert_filename, ssl_key_filename)
            start_server = websockets.serve(self.handler, self.host, self.port, ssl=ssl_context)
            logger.info(f'Relay workflow server ({__name__}) listening on {self.host} port {self.port} with ssl_context {ssl_context}')
        else:
            start_server = websockets.serve(self.handler, self.host, self.port)
            logger.info(f'Relay workflow server ({__name__}) listening on {self.host} port {self.port} with plaintext')

        asyncio.get_event_loop().run_until_complete(start_server)

        try:
            asyncio.get_event_loop().run_forever()

        except KeyboardInterrupt:
            logger.debug('server terminated')

    async def handler(self, websocket, path):
        logger.debug('received new request')
        workflow = self.workflows.get(path, None)
        if workflow:
            logger.debug(f'handling request on path {path}')
            relay = Relay(workflow)
            await relay.handle(websocket)

        else:
            logger.warning(f'ignoring request for unregistered path {path}')
            websocket.close()


class ServerException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Workflow:
    def __init__(self, name):
        self.name = name
        self.type_handlers = {}  # {(type, args): func}

    def on_start(self, func):
        self.type_handlers[('wf_api_start_event')] = func

    def on_stop(self, func):
        self.type_handlers[('wf_api_stop_event')] = func

    ####### TODO: should this be simply on_prompt_event like the message is?

    def on_prompt_start(self, func):
        self.type_handlers[('wf_api_prompt_start_event')] = func

    def on_prompt_stop(self, func):
        self.type_handlers[('wf_api_prompt_stop_event')] = func

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

    def get_handler(self, event):
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
    def __init__(self, message):
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
    def __init__(self, workflow):
        self.workflow = workflow
        self.websocket = None
        self.id_futures = {}  # {_id: future}
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
                    allInt = false;
                    break;
            if allInt and (len(dictMessage) > 0):
                dictMessage = "".join(chr(i) for i in dictMessage)
        return dictMessage

    async def handle(self, websocket):
        self.websocket = websocket
        self.logger = CustomAdapter(logger, {'cid': self.get_cid()})

        self.logger.info(f'workflow started from {self.websocket.path}')

        try:
            async for m in websocket:
                self.logger.debug(f'recv: {m}')
                e = self.fromJson(m)
                _id = e.get('_id', None)
    
                if _id:
                    fut = self.id_futures.pop(_id, None)
                    if fut:
                        fut.set_result(e)
    
                    else:
                        self.logger.warning(f'found response for unknown _id {_id}')
    
                else:
                    h = self.workflow.get_handler(e)
                    if h:
                        t = e['_type']
                        if t == 'wf_api_start_event':
                            logger.debug(f"handle start_event with trigger: {e['trigger']}")
                            asyncio.create_task(self.wrapper(h, e['trigger']))

                        elif t == 'wf_api_stop_event':
                            logger.debug(f"handle stop_event with reason: {e['reason']}")
                            asyncio.create_task(self.wrapper(h, e['reason']))
    
                        elif t == 'wf_api_prompt_start_event':
                            logger.debug(f"handle prompt_start_event with source_uri: {e['source_uri']}, id: {e['id']}")
                            asyncio.create_task(self.wrapper(h, e['source_uri']))

                        elif e['type'] == 'wf_api_prompt_stop_event':
                            logger.debug(f"handle prompt_stop_event with source_uri: {e['source_uri']}, id: {e['id']}")
                            asyncio.create_task(self.wrapper(h, e['source_uri']))

    
                        elif t == 'wf_api_button_event':
                            logger.debug(f"wf_api_button_event with button: {e['button']}, taps: {e['taps']}, source_uri: {e['source_uri']}")
                            asyncio.create_task(self.wrapper(h, e['button'], e['taps'], e['source_uri']))
    
                        elif t == 'wf_api_notification_event':
                            logger.debug(f"wf_api_notification_event with source_uri: {e['source_uri']}, name: {e['name']}, notification_state: {e['notification_state']}")
                            asyncio.create_task(self.wrapper(h, e['event'], e['name'], e['notification_state'], e['source_uri']))
    
                        elif t == 'wf_api_timer_event':
                            logger.debug(f"wf_api_timer_event")
                            asyncio.create_task(self.wrapper(h))

                        elif t == 'wf_api_timer_fired_event':
                            logger.debug(f"wf_api_timer_fired_event, name={e['name']}")
                            asyncio.create_task(self.wrapper(h, e['name']))

                        elif t == 'wf_api_speech_event':
                            logger.debug(f"wf_api_speech_event: text: {text}, audio: {audio}, lang: {lang}, request_id: {request_id}, source_uri{source_uri}")
                            asyncio.create_task(self.wrapper(h, e['text'], e['audio'], e['lang'], e['request_id'], e['source_uri']))

                        elif t == 'wf_api_progress_event':
                            logger.debug(f"wf_api_progress_event: _id: {_id}")
                            asyncio.create_task(self.wrapper(h))

                        elif t == 'wf_api_play_inbox_message_event':
                            logger.debug(f"wf_api_play_inbox_message_event with action: {e['action']}")
                            asyncio.create_task(self.wrapper(h, e['action']))

                        elif t == 'wf_api_call_connected_event':
                            logger.debug(f"wf_api_call_connected_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch'], e['connect_time_epoch']))

                        elif t == 'wf_api_call_disconnected_event':
                            logger.debug(f"wf_api_call_disconnected_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['reason'], e['start_time_epoch'], e['connect_time_epoch'], e['end_time_epoch']))

                        elif t == 'wf_api_call_failed_event':
                            logger.debug(f"wf_api_call_failed_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['reason'], e['start_time_epoch'], e['connect_time_epoch'], e['end_time_epoch']))
    
                        elif t == 'wf_api_call_received_event':
                            logger.debug(f"wf_api_call_received_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch']))
    
                        elif t == 'wf_api_call_ringing_event':
                            logger.debug(f"wf_api_call_ringing_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch']))
    
                        elif t == 'wf_api_call_progressing_event':
                            logger.debug(f"wf_api_call_progressing_event with e: {e}")
                            asyncio.create_task(self.wrapper(h, e['call_id'], e['direction'], e['device_id'], e['device_name'], e['uri'], e['onnet'], e['start_time_epoch'], e['connect_time_epoch']))
    
                        elif t == 'wf_api_call_start_request_event':
                            logger.debug(f"wf_api_call_start_request_event with uri: {e['uri']}")
                            asyncio.create_task(self.wrapper(h, e['uri']))
    
                        elif t == 'wf_api_sms_event':
                            logger.debug(f"wf_api_sms_event with id: {e['id']}, event: {e['event']}")
                            asyncio.create_task(self.wrapper(h, e['id'], e['event']))
    
                        elif t == 'wf_api_incident_event':
                            logger.debug(f"wf_api_incident_event with type: {e['type']}, id: {e['id']}, reason: {e['reason']}")
                            asyncio.create_task(self.wrapper(h, e['type'], e['id'], e['reason']))
    
                        elif t == 'wf_api_interaction_lifecycle_event':
                            logger.debug(f"wf_api_interaction_lifecycle_event with type: {e['type']}, reason: {e['reason']}, source_uri: {e['source_uri']}")
                            asyncio.create_task(self.wrapper(h, e['type'], e['reason'], e['source_uri']))
    
                        elif t == 'wf_api_resume_event':
                            logger.debug(f"wf_api_resume_event with trigger: {e['trigger']}")
                            asyncio.create_task(self.wrapper(h, e['trigger']))
    
                    else:
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


    async def sendReceive(self, obj):
        _id = uuid.uuid4().hex
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


    async def get_var(self, name: str, default=None):
        ### TODO: look in self.workflow.state to see all of what is available
        event = {
            '_type': 'wf_api_get_var_request',
            'name': name
        }
        v = await self.sendReceive(event)
        return v.get('value', default)

    async def set_var(self, name: str, value: str):
        event = {
            '_type': 'wf_api_set_var_request',
            'name': name,
            'value': value
        }
        response = await self.sendReceive(event)
        return response['value']

    async def unset_var(self, name: str):
        event = {
            '_type': 'wf_api_unset_var_request',
            'name': name
        }
        await self.sendReceive(event)

    async def unset_var(self, name: str):
        event = {
            '_type': 'wf_api_unset_var_request',
            'name': name
        }
        await self.sendReceive(event)

    async def interaction_options(color="0000ff", input_types=[], home_channel="suspend"):
        options = {
            'color': color,
            'input_types': input_types,
            'home_channel': home_channel
        }
        return options

    async def start_interaction(self, target, name: str, options=None):
        event = {
            '_type': 'wf_api_start_interaction_request',
            '_target': target,
            'name': name,
            'options': options
        }
        await self.sendReceive(event)

    async def end_interaction(self, target, name: str):
        event = {
            '_type': 'wf_api_end_interaction_request',
            '_target': target,
            'name': name
        }
        await self.sendReceive(event)

    async def listen(self, target, request_id, phrases=None, transcribe=True, timeout=60, alt_lang=None):
        if phrases is None:
            phrases = [ ]
        if instanceof(phrases, str):
            phrases = [ phrases ]

        event = {
            '_type': 'wf_api_listen_request',
            '_target': target,
            'request_id': request_id,
            'phrases': phrases,
            'transcribe': transcribe,
            'timeout': timeout,
            'alt_lang': alt_lang
        }
        await self.sendReceive(event)

    async def play(self, target, filename):
        event = {
            '_type': 'wf_api_play_request',
            '_target': target,
            'filename': filename
        }
        response = await self.sendReceive(event)
        return response['id']

    async def say(self, target, text, lang):
        event = {
            '_type': 'wf_api_say_request',
            '_target': target,
            'text': text,
            'lang': lang
        }
        response = await self.sendReceive(event)
        return response['id']

    # target properties: uri: array of string ids

    async def push_options(self, priority='normal', title=None, body=None, sound='default'):
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
        

    async def broadcast(self, target, originator: str, text: str, targets, name=None, push_options=None):
        await self._notify(target, originator, 'broadcast', name, text, targets, push_options)
    
    async def cancel_broadcast(self, target, name: str, targets):
        await self._notify(target, None, 'cancel', name, None, targets, None)

    async def notify(self, target, originator: str, text: str, targets, name=None, push_options=None):
        await self._notify(target, originator, 'notify', name, text, targets, push_options)
    
    async def cancel_notification(self, target, name: str, targets):
        await self._notify(target, None, 'cancel', name, None, targets, None)

    async def alert(self, target, originator: str, text: str, targets, name=None, push_options=None):
        await self._notify(target, originator, 'alert', name, text, targets, push_options)
    
    async def cancel_alert(self, target, name: str, targets):
        await self._notify(target, None, 'cancel', name, None, targets, None)

    # text is used for creating an "ibot" notification. push_opts allows the developer to customize the push notification sent to a virtual device receiving the created notification

    async def _notify(self, target, originator, ntype, name, text, targets, push_options=None):
        event = {
            '_type': 'wf_api_notification_request',
            '_target': target,
            'originator': originator,
            'type': ntype,
            'name': name,
            'text': text,
            'target': targets,
            'push_opts': push_options
        }
        await self.sendReceive(event)


    async def set_channel(self, target, channel_name: str, suppress_tts=False, disable_home_channel=False):
        event = {
            '_type': 'wf_api_set_channel_request',
            '_target': target,
            'channel_name': channel_name,
            'suppress_tts': suppress_tts,
            'disable_home_channel': disable_home_channel
        }
        await self.sendReceive(event)


    async def get_device_name(self, target, refresh=False):
        v = await self._get_device_info(target, 'name', refresh)
        return v['name']

    async def get_device_address(self, target, refresh=False):
        v = await self._get_device_info(target, 'address', refresh)
        return v['address']

    async def get_device_latlong(self, target, refresh=False):
        v = await self._get_device_info(target, 'latlong', refresh)
        return v['latlong']

    async def get_device_indoor_location(self, target, refresh=False):
        v = await self._get_device_info(target, 'indoor_location', refresh)
        return v['indoor_location']

    async def get_device_battery(self, target, refresh=False):
        v = await self._get_device_info(target, 'battery', refresh)
        return v['battery']

    async def get_device_type(self, target, refresh=False):
        v = await self._get_device_info(target, 'type', refresh)
        return v['type']
    
    async def get_device_id(self, target, refresh=False):
        v = await self._get_device_info(target, 'id', refresh)
        return v['id']

    async def get_device_username(self, target, refresh=False):
        v = await self._get_device_info(target, 'username', refresh)
        return v['username']

    async def get_device_location_enabled(self, target, refresh=False):
        v = await self._get_device_info(target, 'location_enabled', refresh)
        return v['location_enabled']

    async def _get_device_info(self, target, query, refresh):
        event = {
            '_type': 'wf_api_get_device_info_request',
            '_target': target,
            'query': query,
            'refresh': refresh
        }
        v = await self.sendReceive(event)
        return v


    async def set_device_name(self, target, name):
        await self._set_device_info(target, 'label', name)

    async def set_device_channel(self, target, channel: str):
        await self._set_device_info(target, 'channel', channel)

    async def set_device_location_enabled(self, target, location_enabled: str):
        await self._set_device_info(target, 'location_enabled', channel)

    async def _set_device_info(self, target, field, value):
        event = {
            '_type': 'wf_api_set_device_info_request',
            '_target': target,
            'field': field,
            'value': value
        }
        v = await self.sendReceive(event)
        return event

    async def set_device_mode(self, target, mode='none'):
        # values for mode: "panic", "alarm", "none"
        event = {
            '_type': 'wf_api_set_device_mode_request',
            'target': target,
            'mode': mode,
        }
        await self.sendReceive(event)

    async def led_info(self, rotations=None, count=None, duration=None, repeat_delay=None, pattern_repeats=None, colors=None):
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

    async def set_led(self, target, effect="flash", args=None):
        # effect possible values: "rainbow", "rotate", "flash", "breathe", "static", "off"
        # use led_info to create args
        event = {
            '_type': 'wf_api_set_led_request',
            'effect': effect,
            'args': args
        }
        await self.sendReceive(event)

    # convenience functions
    async def set_led_on(self, color):
        await self.set_led('static', {'colors':{'ring': color}})

    async def set_single_led_on(self, index, color):
        await self.set_led('static', {'colors':{f'{index}': color}})

    async def set_led_rainbow(self, rotations=-1):
        await self.set_led('rainbow', {'rotations': rotations})

    async def set_led_flash(self, color, count=-1):
        await self.set_led('flash', {'colors': {'ring': color}, 'count': count})

    async def set_led_breathe(self, color, count=-1):
        await self.set_led('breathe', {'colors': {'ring': color}, 'count': count})

    async def set_led_rotate(self, color, rotations=-1):
        await self.set_led('rotate', {'colors': {'1': color}, 'rotations': rotations})

    async def set_led_off(self):
        await self.set_led('off', {})


    async def vibrate(self, target, pattern=None):
        if not pattern:
            pattern = [100, 500, 500, 500, 500, 500]

        event = {
            '_type': 'wf_api_vibrate_request',
            '_target': target,
            'pattern': pattern
        }
        await self.sendReceive(event)

    # unnamed timer
    async def start_timer(self, timeout: int):
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


    async def create_incident(self, originator, itype):
        # TODO: what are the values for itype?
        event = {
            '_type': 'wf_api_create_incident_request',
            'type': itype,
            'originator_uri': originator
        }
        v = await self.sendReceive(event)
        return v['incident_id']

    async def resolve_incident(self, incident_id: str, reason: str):
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
    
    async def stop_playback(self, target, id=None):
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

    async def translate(self, text, from_lang, to_lang):
        event = {
            '_type': 'wf_api_translate_request',
            'text': text,
            'from_lang': from_lang,
            'to_lang': to_lang
        }
        response = await self.sendReceive(event)
        return response['text']

    async def place_call(self, target, uri: str):
        event = {
            '_type': 'wf_api_call_request',
            '_target': target,
            'uri': uri
        }
        response = await self.sendReceive(event)
        return response['call_id']

    async def answer_call(self, target, call_id: str):
        event = {
            '_type': 'wf_api_answer_request',
            '_target': target,
            'call_id': call_id
        }
        await self.sendReceive(event)
    
    async def hangup_call(self, target, call_id: str):
        event = {
            '_type': 'wf_api_hangup_request',
            '_target': target,
            'call_id': call_id
        }
        await self.sendReceive(event)

    ##### TODO: test me from this point down


    ## TODO: has this one been superceded by wf_api_group_query_request?
    async def list_group_members(self, group_name: str):
        event = {
            '_type': 'wf_api_list_group_members_request',
            'group_name': group_name
        }
        await self.sendReceive(event)

    async def group_query_members(self, group_uri: str):
        event = {
            '_type': 'wf_api_group_query_request',
            'query': 'list_members',
            'group_uri': group_uri
        }
        response = await self.sendReceive(event)
        return response['member_uris']

    async def group_query_is_member(self, group_uri: str):
        event = {
            '_type': 'wf_api_group_query_request',
            'query': 'is_member',
            'group_uri': group_uri
        }
        response = await self.sendReceive(event)
        return response['is_member']
        

    async def set_user_profile(self, target: str, username: str, force=False):
        event = {
            '_type': 'wf_api_set_user_profile_request',
            '_target': target,
            'username': username,
            'force': force
        }
        await self.sendReceive(event)

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

    async def log_analytics_event(self, content: str, content_type: str, category: str, device_url=None):
        event = {
            '_type': 'wf_api_log_analytics_event_request',
            'content': content,
            'content_type': content_type,
            'category': category,
            'device_url': device_url
        }
        await self.sendReceive(event)

    # named timer
    async def set_timer(self, name: str, timeout: int, ttype: 'timeout'):
        event = {
            '_type': 'wf_api_set_timer_request',
            'type': ttype,
            'name': name,
            'timeout': timeout
        }
        await self.sendReceive(event)

    # named timer
    async def clear_timer(self, name: str):
        event = {
            '_type': 'wf_api_clear_timer_request',
            'name': name
        }
        await self.sendReceive(event)

    async def sms(self, stype: str, text: str, uri: str):
        event = {
            '_type': 'wf_api_sms_request',
            'type': stype,
            'text': text,
            'uri': uri
        }
        response = await self.sendReceive(event)
        return response['message_id']

    async def set_home_channel_state(self, target, enabled=True):
        event = {
            '_type': 'wf_api_set_home_channel_state_request',
            '_target': target,
            'enabled': enabled
        }
        await self.sendReceive(event)

    async def register(self, target, uri: str, password: str, expires: int):
        event = {
            '_type': 'wf_api_register_request',
            '_target': target,
            'uri': uri,
            'password': password,
            'expires': expires
        }
        await self.sendReceive(event)

    async def invalid_type(self):
        event = {
            '_type': 'wf_api_mkinard_breakage',
            'device_id': 'TheQuickBrownFoxJumpsOverTheLazyDog',
            'call_id': 'you can\'t catch me'
        }
        await self.sendReceive(event)

    async def missing_type(self):
        event = {
            'device_id': 'NowIsTheTimeToComeToTheAidOfYourCountry',
            'call_id': 'you can\'t catch me'
        }
        await self.sendReceive(event)
