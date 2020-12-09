#!/usr/bin/env python

import asyncio
import json
import pytest
import websockets


@pytest.fixture(scope='module')
def wf_server():
    import relay.workflow
    import all_features

    import threading

    server = relay.workflow.Server('localhost', 8765)
    server.register(all_features.wf, '/hello')

    def wrapped_start():
        asyncio.set_event_loop(asyncio.new_event_loop())
        server.start()

    thread = threading.Thread(target=wrapped_start)
    thread.daemon = True
    thread.start()


async def send(ws, e):
    s = json.dumps(e)
    print(f'> {s}')
    await ws.send(s)

async def recv(ws):
    s = await ws.recv()
    print(f'< {s}')
    return json.loads(s)

def check(event, etype, **kwargs):
    assert event['_type'] == etype
    for (k, v) in kwargs.items():
        assert event[k] == v, f'for {k}, {v} != {event[k]}'


async def send_start(ws):
    await send(ws, {
        '_type': 'wf_api_start_event'})

async def handle_get_var(ws, xname, value):
    e = await recv(ws)
    check(e, 'wf_api_get_var_request', name=xname)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_get_var_response',
        'value': value})

async def handle_set_var(ws, xname, xvalue, vtype):
    e = await recv(ws)
    check(e, 'wf_api_set_var_request', name=xname, value=xvalue)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_var_response',
        'name': xname,
        'value': xvalue,
        'type': vtype})

async def handle_listen(ws, xphrases, text, audio=''):
    e = await recv(ws)
    check(e, 'wf_api_listen_request', phrases=xphrases, transcribe=True, timeout=60)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_listen_response',
        'text': text,
        'audio': audio})

async def handle_play(ws, xname):
    e = await recv(ws)
    check(e, 'wf_api_play_request', filename=xname)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_play_response'})


async def handle_say(ws, xtext):
    e = await recv(ws)
    check(e, 'wf_api_say_request', text=xtext)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_say_response'})


async def handle_notification(ws, xtype, xtext, xtarget):
    e = await recv(ws)
    check(e, 'wf_api_notification_request', type=xtype, text=xtext, target=xtarget)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_say_response'})


async def handle_get_device_name(ws, xrefresh, name):
    await _handle_get_device_info(ws, 'name', xrefresh, name=name)
 
async def handle_get_device_location(ws, xrefresh, address, latlong):
    await _handle_get_device_info(ws, 'location', xrefresh, address=address, latlong=latlong)

async def handle_get_device_indoor_location(ws, xrefresh, indoor_location):
    await _handle_get_device_info(ws, 'indoor_location', xrefresh, indoor_location=indoor_location)

async def handle_get_device_battery(ws, xrefresh, battery):
    await _handle_get_device_info(ws, 'battery', xrefresh, battery=battery)

async def _handle_get_device_info(ws, xquery, xrefresh, **kwargs):
    e = await recv(ws)
    check(e, 'wf_api_get_device_info_request', query=xquery, refresh=xrefresh)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_get_device_info_response',
        **kwargs})


async def handle_set_device_name(ws, xvalue):
    await _handle_set_device_info(ws, 'name', xvalue)

async def handle_set_device_channel(ws, xvalue):
    await _handle_set_device_info(ws, 'channel', xvalue)

async def _handle_set_device_info(ws, xfield, xvalue):
    e = await recv(ws)
    check(e, 'wf_api_set_device_info_request', field=xfield, value=xvalue)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_device_info_response',
    })


async def handle_set_led_on(ws, xcolor):
    await _handle_set_led(ws, 'static', {'colors':{'ring': xcolor}})

async def handle_set_led_rainbow(ws, xrotations):
    await _handle_set_led(ws, 'rainbow', {'rotations': xrotations})

async def handle_set_led_flash(ws, xcolor, xcount):
    await _handle_set_led(ws, 'flash', {'colors': {'ring': xcolor}, 'count': xcount})

async def handle_set_led_breathe(ws, xcolor, xcount):
    await _handle_set_led(ws, 'breathe', {'colors': {'ring': xcolor}, 'count': xcount})

async def handle_set_led_rotate(ws, xcolor, xrotations):
    await _handle_set_led(ws, 'rotate', {'colors': {'1': xcolor}, 'rotations': xrotations})

async def handle_set_led_off(ws):
    await _handle_set_led(ws, 'off', {})

async def _handle_set_led(ws, xeffect, xargs):
    e = await recv(ws)
    check(e, 'wf_api_set_led_request', effect=xeffect, args=xargs)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_led_response'})


async def handle_vibrate(ws, xpattern):
    e = await recv(ws)
    check(e, 'wf_api_vibrate_request', pattern=xpattern)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_vibrate_response'})


async def handle_start_timer(ws, xtimeout):
    e = await recv(ws)
    check(e, 'wf_api_start_timer_request', timeout=xtimeout)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_start_timer_response'})


async def handle_stop_timer(ws):
    e = await recv(ws)
    check(e, 'wf_api_stop_timer_request')
  
    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_stop_timer_response'})


async def handle_create_incident(ws, xtype):
    e = await recv(ws)
    check(e, 'wf_api_create_incident_request', type=xtype)
    
    # TODO: add response, when available

async def handle_resolve_incident(ws):
    e = await recv(ws)
    check(e, 'wf_api_resolve_incident_request')

    # TODO: add response, when available


async def handle_terminate(ws):
    e = await recv(ws)
    check(e, 'wf_api_terminate_request')

    # TODO: add response, when available


async def send_button(ws, button, taps):
    await send(ws, {
        '_type': 'wf_api_button_event',
        'button': button,
        'taps': taps})

    
async def send_notification(ws, source, event):
    await send(ws, {
        '_type': 'wf_api_notification_event',
        'source': source,
        'event': event})


async def send_timer(ws):
    await send(ws, {
        '_type': 'wf_api_timer_event'})



async def handle_set_device_name(ws, xvalue):
    await _handle_set_device_info(ws, 'name', xvalue)

async def _handle_set_device_info(ws, xfield, xvalue):
    e = await recv(ws)
    check(e, 'wf_api_set_device_info_request', field=xfield, value=xvalue)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_device_info_response',
    })


async def simple():
    uri = "ws://localhost:8765/hello"
    async with websockets.connect(uri) as ws:
        await send_start(ws)

        await handle_get_var(ws, 'k', 'v')
        await handle_set_var(ws, 'k', 'v', 'string')

        await handle_listen(ws, [], 't')
        await handle_listen(ws, ['p1', 'p2'], 't')
        await handle_play(ws, 'f')
        await handle_say(ws, 't')

        await handle_notification(ws, 'broadcast', 't', ['d1', 'd2'])
        await handle_notification(ws, 'background', 't', ['d1', 'd2'])
        await handle_notification(ws, 'foreground', 't', ['d1', 'd2'])

        await handle_get_device_name(ws, False, 't')
        await handle_get_device_location(ws, False, 'a', [1,2])
        await handle_get_device_indoor_location(ws, False, 'l')
        await handle_get_device_battery(ws, False, 90)


        # receive next request, but inject a button event before response
        # this verifies that the workflow can handle asynchronous requests
        e = await recv(ws)
        check(e, 'wf_api_set_device_info_request', field='name', value='n')

        # inject button event
        await send_button(ws, 'action', 'single')
        await handle_say(ws, 'handle_action_single_tap(action, single)')

        # complete the above request
        await send(ws, {
            '_id': e['_id'],
            '_type': 'wf_api_set_device_info_response',
        })


        await handle_set_device_channel(ws, 'c')

        await handle_set_led_on(ws, '00FF00')
        await handle_set_led_rainbow(ws, -1)
        await handle_set_led_rainbow(ws, 5)
        await handle_set_led_flash(ws, '00FF00', -1)
        await handle_set_led_flash(ws, '00FF00', 5)
        await handle_set_led_breathe(ws, '00FF00', -1)
        await handle_set_led_breathe(ws, '00FF00', 5)
        await handle_set_led_rotate(ws, '00FF00', -1)
        await handle_set_led_rotate(ws, '00FF00', 5)
        await handle_set_led_off(ws)

        await handle_vibrate(ws, [100, 500, 500, 500, 500, 500])
        await handle_vibrate(ws, [100, 200, 300])

        await handle_start_timer(ws, 10)
        await handle_stop_timer(ws)

        await handle_create_incident(ws, 'i')
        await handle_resolve_incident(ws)

        await handle_terminate(ws)

        await send_button(ws, 'action', 'single')
        await handle_say(ws, 'handle_action_single_tap(action, single)')

        await send_button(ws, 'action', 'double')
        await handle_say(ws, 'handle_action(action, double)')

        await send_button(ws, 'channel', 'double')
        await handle_say(ws, 'handle_double_tap(channel, double)')

        await send_button(ws, 'channel', 'single')
        await handle_say(ws, 'handle_button(channel, single)')

        await send_notification(ws, 's1', 'e1')
        await handle_say(ws, 'handle_notification(s1, e1)')

        await send_timer(ws)
        await handle_say(ws, 'handle_timer()')


def test_simple(wf_server):
    asyncio.get_event_loop().run_until_complete(simple())
