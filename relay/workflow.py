import asyncio
import json
import logging
import time
import uuid
import websockets


logger = logging.getLogger(__name__)


class Workflow:
    def __init__(self, host, port):
        self.id_futures = {}
        self.type_handlers = {}

        start_server = websockets.serve(self.handler, host, port)
        asyncio.get_event_loop().run_until_complete(start_server)

    async def handler(self, websocket, path):
        self.relay = Relay(self)
        self.websocket = websocket

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
                t = e['_type']
                h = self.type_handlers.get(t)
                if h:
                    if t == 'wf_api_start_event':
                        asyncio.create_task(h(self.relay))

                    elif t == 'wf_api_button_event':
                        asyncio.create_task(h(self.relay, e['button'], e['taps']))

                    elif t == 'wf_api_notification_event':
                        asyncio.create_task(h(self.relay, e['source'], e['event']))

                    elif t == 'wf_api_timer_event':
                        asyncio.create_task(h(self.relay))

                else:
                    logger.warning(f"no handler found for _type {e['_type']}")

 
    def on_start(self, func):
        self.type_handlers['wf_api_start_event'] = func

    def on_button(self, func):
        self.type_handlers['wf_api_button_event'] = func

    def on_notification(self, func):
        self.type_handlers['wf_api_notification_event'] = func

    def on_timer(self, func):
        self.type_handlers['wf_api_timer_event'] = func


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


class WorkflowException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class Relay:
    def __init__(self, workflow):
        self.workflow = workflow

    def _get_device_info_request(self, query: str, refresh: bool):
        event = {
            '_type': 'wf_api_get_device_info_request',
            'query': query,
            'refresh': refresh
        }
        return event

    def _set_device_info_request(self, field: str, value: str):
        event = {
            '_type': 'wf_api_set_device_info_request',
            'field': field,
            'value': value
        }
        return event


    async def get_var(self, name: str):
        event = {
            '_type': 'wf_api_get_var_request',
            'name': name
        }
        v = await self.workflow.sendReceive(event)
        return v['value']

    async def get_device_name(self):
        event = self._get_device_info_request('name', False)
        v = await self.workflow.sendReceive(event)
        return v['name']

    async def get_device_location(self, refresh: bool):
        # TODO: also return latlong?
        event = _get_device_info_request('location', refresh)
        v = await self.workflow.sendReceive(event)
        return v['address']

    async def get_device_indoor_location(self, refresh: bool):
        event = _get_device_info_request('indoor_location', refresh)
        v = await self.workflow.sendReceive(event)
        return v['indoor_location']

    async def get_device_battery(self):
        event = _get_device_info_request('battery', False)
        v = await self.workflow.sendReceive(event)
        return v['battery']

    async def listen(self, phrases):
        event = {
            '_type': 'wf_api_listen_request',
            'phrases': phrases,
            'transcribe': True,
            'timeout': 60
        }
        v = await self.workflow.sendReceive(event)
        return v['text']

    async def notify(self, ntype, text, targets):
        event = {
            '_type': 'wf_api_notification_request',
            'type': ntype,
            'text': text,
            'target': targets
        }
        await self.workflow.send(event)

    async def play(self, fname):
        event = {
            '_type': 'wf_api_play_request',
            'filename': fname
        }
        await self.workflow.send(event)

    async def say(self, text):
        event = {
            '_type': 'wf_api_say_request',
            'text': text
        }
        await self.workflow.send(event)

    async def set_device_name(self, name):
        event = _set_device_info_request('name', name)
        await self.workflow.sendReceive(event)

    async def set_device_channel(self, channel: str):
        event = _set_device_info_request('channel', channel)
        await self.workflow.sendReceive(event)

    async def set_led(self, effect: str, args):
        event = {
            '_type': 'wf_api_set_led_request',
            'effect': effect,
            'args': args
        }
        await self.workflow.send(event)

    async def set_var(self, name: str, value: str):
        event = {
            '_type': 'wf_api_set_var_request',
            'name': name,
            'value': value
        }
        await self.workflow.send(event)

    async def start_timer(self, timeout: int):
        event = {
            '_type': 'wf_api_start_timer_request',
            'timeout': timeout
        }
        await self.workflow.send(event)

    async def stop_timer(self):
        event = {
            '_type': 'wf_api_stop_timer_request'
        }
        await self.workflow.send(event)

    async def terminate(self):
        event = {
            '_type': 'wf_api_terminate_request'
        }
        await self.workflow.send(event)

    async def vibrate(self, pattern):
        event = {
            '_type': 'wf_api_vibrate_request',
            'pattern': pattern
        }
        await self.workflow.send(event)

