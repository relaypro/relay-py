#!/usr/bin/env python

import asyncio
import json
import websockets


async def send(ws, e):
    s = json.dumps(e)
    print(f'> {s}')
    await ws.send(s)


async def recv(ws):
    s = await ws.recv()
    print(f'< {s}')
    return json.loads(s)


async def simple():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        await send(ws, {
            '_type': 'wf_api_start_event'
        })


        e = await recv(ws)
        assert e['_type'] == 'wf_api_get_var_request'
        assert e['name'] == 'greeting'

        # use _id from request to mark this response
        await send(ws, {
            '_id': e['_id'],
            '_type': 'wf_api_get_var_response',
            'value':'Welcome'
        })


        e = await recv(ws)
        assert e['_type'] == 'wf_api_get_device_info_request'
        assert e['query'] == 'name'

        await send(ws, {
            '_id': e['_id'],
            '_type': 'wf_api_get_device_info_response',
            'name': 'device 1'
        })


        e = await recv(ws)
        assert e['_type'] == 'wf_api_say_request'
        assert e['text'] == 'What is your name?'


        e = await recv(ws)
        assert e['_type'] == 'wf_api_listen_request'
        assert e['phrases'] == []

        await send(ws, {
            '_id': e['_id'],
            '_type': 'wf_api_listen_response',
            'text': 'Bob'
        })


        e = await recv(ws)
        assert e['_type'] == 'wf_api_say_request'
        assert e['text'] == 'Hello Bob! Welcome device 1'


        e = await recv(ws)
        assert e['_type'] == 'wf_api_terminate_request'

asyncio.get_event_loop().run_until_complete(simple())

