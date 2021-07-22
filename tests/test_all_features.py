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

async def handle_unset_var(ws, xname):
    e = await recv(ws)
    check(e, 'wf_api_unset_var_request', name=xname)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_unset_var_response',
        'name': xname
    })

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


async def handle_broadcast(ws, xtext, xtarget):
    e = await recv(ws)
    check(e, 'wf_api_notification_request', type='broadcast', text=xtext, target=xtarget)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_say_response'})

async def handle_notify(ws, xtext, xtarget):
    e = await recv(ws)
    check(e, 'wf_api_notification_request', type='notify', text=xtext, target=xtarget)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_say_response'})

async def handle_alert(ws, xtext, xtarget, xname=None):
    e = await recv(ws)
    if xname:
        check(e, 'wf_api_notification_request', type='alert', text=xtext, target=xtarget, name=xname)
    else:
        check(e, 'wf_api_notification_request', type='alert', text=xtext, target=xtarget)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_say_response'})

async def handle_cancel_notification(ws, xname, xtarget=None):
    e = await recv(ws)
    if xtarget:
        check(e, 'wf_api_notification_request', type='cancel', name=xname, target=xtarget)
    else:
        check(e, 'wf_api_notification_request', type='cancel', name=xname)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_say_response'})

async def handle_cancel_alert(ws, xname, xtarget=None):
    await handle_cancel_notification(ws, xname, xtarget)

async def handle_cancel_broadcast(ws, xname, xtarget=None):
    await handle_cancel_notification(ws, xname, xtarget)

async def _handle_notification(ws, xtype, xname, xtext, xtarget):
    e = await recv(ws)
    check(e, 'wf_api_notification_request', name=xname, type=xtype, text=xtext, target=xtarget)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_say_response'})


async def handle_set_channel(ws, xchannel_name, xtarget):
    e = await recv(ws)
    check(e, 'wf_api_set_channel_request', channel_name=xchannel_name, target=xtarget)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_channel_response'})


async def handle_get_device_name(ws, xrefresh, name):
    await _handle_get_device_info(ws, 'name', xrefresh, name=name)
 
async def handle_get_device_address(ws, xrefresh, address):
    await _handle_get_device_info(ws, 'address', xrefresh, address=address)

async def handle_get_device_latlong(ws, xrefresh, latlong):
    await _handle_get_device_info(ws, 'latlong', xrefresh, latlong=latlong)

async def handle_get_device_indoor_location(ws, xrefresh, indoor_location):
    await _handle_get_device_info(ws, 'indoor_location', xrefresh, indoor_location=indoor_location)

async def handle_get_device_battery(ws, xrefresh, battery):
    await _handle_get_device_info(ws, 'battery', xrefresh, battery=battery)

async def handle_get_device_type(ws, xrefresh, type):
    await _handle_get_device_info(ws, 'type', xrefresh, type=type)

async def handle_get_device_id(ws, xrefresh, xid):
    await _handle_get_device_info(ws, 'id', xrefresh, id=xid)

async def _handle_get_device_info(ws, xquery, xrefresh, **kwargs):
    e = await recv(ws)
    check(e, 'wf_api_get_device_info_request', query=xquery, refresh=xrefresh)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_get_device_info_response',
        **kwargs})


async def handle_set_device_name(ws, xvalue):
    await _handle_set_device_info(ws, 'label', xvalue)

async def handle_set_device_channel(ws, xvalue):
    await _handle_set_device_info(ws, 'channel', xvalue)

async def _handle_set_device_info(ws, xfield, xvalue):
    e = await recv(ws)
    check(e, 'wf_api_set_device_info_request', field=xfield, value=xvalue)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_device_info_response',
    })

async def handle_set_device_mode(ws, xmode, xtarget=None):
    e = await recv(ws)
    if xtarget:
        check(e, 'wf_api_set_device_mode_request', mode=xmode, target=xtarget)
    else:
        check(e, 'wf_api_set_device_mode_request', mode=xmode)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_device_mode_response',
    })


async def handle_set_led_on(ws, xcolor):
    await _handle_set_led(ws, 'static', {'colors':{'ring': xcolor}})

async def handle_set_single_led_on(ws, xcolor, xindex):
    await _handle_set_led(ws, 'static', {'colors':{f'{xindex}': xcolor}})

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


async def handle_create_incident(ws, xtype, incident_id):
    e = await recv(ws)
    check(e, 'wf_api_create_incident_request', type=xtype)
    
    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_create_incident_response',
        'incident_id': incident_id})


async def handle_resolve_incident(ws, xincident_id, xreason):
    e = await recv(ws)
    check(e, 'wf_api_resolve_incident_request', incident_id=xincident_id, reason=xreason)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_resolve_incident_response'})


async def handle_terminate(ws):
    e = await recv(ws)
    check(e, 'wf_api_terminate_request')

    # TODO: add response, when available


async def send_button(ws, button, taps):
    await send(ws, {
        '_type': 'wf_api_button_event',
        'button': button,
        'taps': taps})

    
async def send_notification(ws, source, name, event, state):
    await send(ws, {
        '_type': 'wf_api_notification_event',
        'source': source,
        'event': event,
        'name': name,
        'notification_state': state})


async def send_timer(ws):
    await send(ws, {
        '_type': 'wf_api_timer_event'})



async def handle_set_device_name(ws, xvalue):
    await _handle_set_device_info(ws, 'label', xvalue)

async def _handle_set_device_info(ws, xfield, xvalue):
    e = await recv(ws)
    check(e, 'wf_api_set_device_info_request', field=xfield, value=xvalue)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_set_device_info_response',
    })

async def handle_restart_device(ws):
    e = await recv(ws)
    check(e, 'wf_api_device_power_off_request')

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_device_power_off_response'})

async def handle_power_down_device(ws):
    e = await recv(ws)
    check(e, 'wf_api_device_power_off_request')

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_device_power_off_response'})

async def handle_stop_playback(ws, xid=None):
    e = await recv(ws)
    if xid:
        check(e, 'wf_api_stop_playback_request', ids=xid)
    else:
        check(e, 'wf_api_stop_playback_request')

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_stop_playback_response',
        'ids': xid})

async def handle_translate(ws, xtext, xfrom, xto):
    e = await recv(ws)
    check(e, 'wf_api_translate_request', text=xtext, from_lang=xfrom, to_lang=xto)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_translate_response',
        'text': xtext,
        'from_lang': xfrom,
        'to_lang': xto
    })

async def handle_place_call(ws, xcall):
    e = await recv(ws)
    check(e, 'wf_api_call_request', call=xcall)

    await send(ws, {
        '_id': e['_id'],
        '_type': 'wf_api_call_response',
        'call': xcall,
    })

async def simple():
    uri = "ws://localhost:8765/hello"
    async with websockets.connect(uri) as ws:
        await send_start(ws)

        await handle_get_var(ws, 'k', 'v')
        await handle_set_var(ws, 'k', 'v', 'string')
        await handle_unset_var(ws, 'k')

        await handle_listen(ws, [], 't')
        await handle_listen(ws, ['p1', 'p2'], 't')
        await handle_play(ws, 'f')
        await handle_say(ws, 't')

        await handle_broadcast(ws, 't', ['d1', 'd2'])
        await handle_notify(ws, 't', ['d1', 'd2'])
        await handle_alert(ws, 't', ['d1', 'd2'])
        await handle_alert(ws, 't', ['d1', 'd2'], 'n')
        await handle_cancel_notification(ws, 'n', ['d1', 'd2'])
        await handle_cancel_alert(ws, 'a', ['d1', 'd2'])
        await handle_cancel_broadcast(ws, 'b', ['d1', 'd2'])

        await handle_set_channel(ws, 'c', ['d1', 'd2'])

        await handle_get_device_name(ws, False, 't')
        await handle_get_device_address(ws, False, 'a')
        await handle_get_device_latlong(ws, False, [1,2])
        await handle_get_device_indoor_location(ws, False, 'l')
        await handle_get_device_battery(ws, False, 90)
        await handle_get_device_type(ws, False, 't')
        await handle_get_device_id(ws, False, 'i')


        # receive next request, but inject a button event before response
        # this verifies that the workflow can handle asynchronous requests
        e = await recv(ws)
        check(e, 'wf_api_set_device_info_request', field='label', value='n')

        # inject button event
        await send_button(ws, 'action', 'single')
        await handle_say(ws, 'handle_action_single_tap(action, single)')

        # complete the above request
        await send(ws, {
            '_id': e['_id'],
            '_type': 'wf_api_set_device_info_response',
        })


        await handle_set_device_channel(ws, 'c')

        await handle_set_device_mode(ws, 'm')
        await handle_set_device_mode(ws, 'm', ['d1', 'd2'])

        await handle_set_led_on(ws, '00FF00')
        await handle_set_single_led_on(ws, '00FF00', 3)
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

        await handle_create_incident(ws, 'i', 'iid')
        await handle_resolve_incident(ws, 'iid', 'r')

        await handle_restart_device(ws)
        await handle_power_down_device(ws)

        await handle_stop_playback(ws, ['1839'])
        await handle_stop_playback(ws, ['1839', '1840', '1850', '1860'])
        await handle_stop_playback(ws)

        await handle_translate(ws, 'Bonjour', 'fr-FR', 'en-US')

        await handle_place_call(ws, 'c')

        await handle_terminate(ws)

        await send_button(ws, 'action', 'single')
        await handle_say(ws, 'handle_action_single_tap(action, single)')

        await send_button(ws, 'action', 'double')
        await handle_say(ws, 'handle_action(action, double)')

        await send_button(ws, 'channel', 'double')
        await handle_say(ws, 'handle_double_tap(channel, double)')

        await send_button(ws, 'channel', 'single')
        await handle_say(ws, 'handle_button(channel, single)')

        await send_notification(ws, 's1', 'n', 'e1', 'state')
        await handle_say(ws, 'handle_notification(s1, n, e1, state)')

        await send_timer(ws)
        await handle_say(ws, 'handle_timer()')


def test_simple(wf_server):
    asyncio.get_event_loop().run_until_complete(simple())

