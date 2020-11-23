import asyncio
import json
import logging
import time
import uuid
import websockets


logger = logging.getLogger(__name__)


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
        start_server = websockets.serve(self.handler, self.host, self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def handler(self, websocket, path):
        workflow = self.workflows.get(path, None)
        if workflow:
            relay = Relay(workflow)
            await relay.handle(websocket)

        else:
            raise ServerException(f'no workflow registered for path {path}')


class ServerException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Workflow:
    def __init__(self, name):
        self.name = name
        self.type_handlers = {}  # {(type, args): func}


    def on_start(self, func):
        key = ('wf_api_start_event')
        self.type_handlers[key] = func

    def on_button(self, _func=None, *, button='*', taps='*'):
        def decorator_on_button(func):
            key = ('wf_api_button_event', button, taps)
            self.type_handlers[key] = func

        if _func:
            return decorator_on_button(_func)

        else:
            return decorator_on_button
    
    def on_notification(self, _func=None, *, event='*', source='*'):
        def decorator_on_notification(func):
            key = ('wf_api_notification_event', event, source)
            self.type_handlers[key] = func

        if _func:
            return decorator_on_notification(_func)

        else:
            return decorator_on_notification


#    def on_notification(self, func):
#        key = ('wf_api_notification_event')
#        self.type_handlers[key] = func

    def on_timer(self, func):
        key = ('wf_api_timer_event')
        self.type_handlers[key] = func


    def get_handler(self, event):
        t = event['_type']

        # assume simple handler; if not, check with args
        key = (t)
        h = self.type_handlers.get(key, None)
        if not h:
            if t == 'wf_api_button_event':
                key = (t, event['button'], event['taps'])
                h = self.type_handlers.get(key, None)
                if not h:
                    key = (t, event['button'], '*')
                    h = self.type_handlers.get(key, None)
                    if not h:
                        key = (t, '*', event['taps'])
                        h = self.type_handlers.get(key, None)
                        if not h:
                            key = (t, '*', '*')
                            h = self.type_handlers.get(key, None)

            elif t == 'wf_api_notification_event':
                key = (t, event['event'], event['source'])
                h = self.type_handlers.get(key, None)
                if not h:
                    key = (t, event['event'], '*')
                    h = self.type_handlers.get(key, None)
                    if not h:
                        key = (t, '*', event['source'])
                        h = self.type_handlers.get(key, None)
                        if not h:
                            key = (t, '*', '*')
                            h = self.type_handlers.get(key, None)

        return h


class WorkflowException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Relay:
    def __init__(self, workflow):
        self.workflow = workflow
        self.websocket = None
        self.id_futures = {}  # {_id: future}

    async def handle(self, websocket):
        self.websocket = websocket

        try:
            async for m in websocket:
                logger.debug(f'recv: {m}')
                e = json.loads(m)
                _id = e.get('_id', None)
    
                if _id:
                    fut = self.id_futures.pop(_id)
                    if fut:
                        fut.set_result(e)
    
                    else:
                        logger.warning(f'found response for unknown _id {_id}')
    
                else:
                    h = self.workflow.get_handler(e)
                    if h:
                        t = e['_type']
                        if t == 'wf_api_start_event':
                            asyncio.create_task(h(self))
    
                        elif t == 'wf_api_button_event':
                            asyncio.create_task(h(self, e['button'], e['taps']))
    
                        elif t == 'wf_api_notification_event':
                            asyncio.create_task(h(self, e['source'], e['event']))
    
                        elif t == 'wf_api_timer_event':
                            asyncio.create_task(h(self))
    
                    else:
                        logger.warning(f'no handler found for _type {e["_type"]}')

        except Exception as x:
            logger.error(x, exc_info=True)

        finally:
            logger.debug('websocket closed')            


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

        await self._send(json.dumps(obj))

        # wait on the response
        await fut

        rsp = fut.result()
        if rsp['_type'] == 'wf_api_error_response':
            raise WorkflowException(rsp['error'])

        return fut.result()


    async def _send(self, s):
        logger.debug(f'send: {s}')
        await self.websocket.send(s)


    async def get_var(self, name: str, default=None):
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
        await self.send(event)


    async def listen(self, phrases):
        event = {
            '_type': 'wf_api_listen_request',
            'phrases': phrases,
            'transcribe': True,
            'timeout': 60
        }
        v = await self.sendReceive(event)
        return v['text']

    async def play(self, fname):
        event = {
            '_type': 'wf_api_play_request',
            'filename': fname
        }
        await self.send(event)

    async def say(self, text):
        event = {
            '_type': 'wf_api_say_request',
            'text': text
        }
        await self.send(event)


    async def broadcast(self, text: str, targets):
        await self._notify('broadcast', text, targets)

    async def notify(self, text: str, targets):
        await self._notify('background', text, targets)

    async def alert(self, text: str, targets):
        await self._notify('foreground', text, targets)

    async def _notify(self, ntype, text, targets):
        event = {
            '_type': 'wf_api_notification_request',
            'type': ntype,
            'text': text,
            'target': targets
        }
        await self.send(event)


    async def get_device_name(self):
        v = await self._get_device_info('name', False)
        return v['name']

    async def get_device_location(self):
        # TODO: also return latlong?
        v = await self._get_device_info('location', False)
        return v['address']

    async def get_device_indoor_location(self):
        v = await self._get_device_info('indoor_location', False)
        return v['indoor_location']

    async def get_device_battery(self):
        v = await self._get_device_info('battery', False)
        return v['battery']

    async def _get_device_info(self, query, refresh):
        event = {
            '_type': 'wf_api_get_device_info_request',
            'query': query,
            'refresh': refresh
        }
        v = await self.sendReceive(event)
        return v


    async def set_device_name(self, name):
        await _set_device_info('name', name)

    async def set_device_channel(self, channel: str):
        await _set_device_info('channel', channel)

    async def _set_device_info(self, field, value):
        event = {
            '_type': 'wf_api_set_device_info_request',
            'field': field,
            'value': value
        }
        v = await self.sendReceive(event)
        return event


    async def set_led(self, effect: str, args):
        event = {
            '_type': 'wf_api_set_led_request',
            'effect': effect,
            'args': args
        }
        await self.send(event)

    # convenience functions
    async def set_led_on(self, color):
        await self.set_led('static', {'colors':{'ring':color}})

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


    async def vibrate(self, pattern=None):
        if not pattern:
            pattern = [100, 500, 500, 500, 500, 500]

        event = {
            '_type': 'wf_api_vibrate_request',
            'pattern': pattern
        }
        await self.send(event)


    async def start_timer(self, timeout: int):
        event = {
            '_type': 'wf_api_start_timer_request',
            'timeout': timeout
        }
        await self.send(event)

    async def stop_timer(self):
        event = {
            '_type': 'wf_api_stop_timer_request'
        }
        await self.send(event)


    async def terminate(self):
        event = {
            '_type': 'wf_api_terminate_request'
        }
        await self.send(event)


    async def create_incident(self, itype):
        event = {
            '_type': 'wf_api_create_incident_request',
            'type': itype
        }
        await self.send(event)

    async def resolve_incident(self):
        event = {
            '_type': 'wf_api_create_incident_request'
        }
        await self.send(event)


