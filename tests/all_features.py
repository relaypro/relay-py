#!/usr/bin/env python

import inspect
import json

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    await relay.get_var('k')
    await relay.set_var('k', 'v')

    await relay.listen()
    await relay.listen(['p1', 'p2'])
    await relay.play('f')
    await relay.say('t')

    await relay.broadcast('t', ['d1', 'd2'])
    await relay.notify('t', ['d1', 'd2'])
    await relay.alert('t', ['d1', 'd2'])
    await relay.alert('t', ['d1', 'd2'], name='n')
    await relay.cancel_notification('n', ['d1', 'd2'])

    await relay.set_channel('c', ['d1', 'd2'])

    await relay.get_device_name()
    await relay.get_device_address()
    await relay.get_device_latlong()
    await relay.get_device_indoor_location()
    await relay.get_device_battery()
    await relay.get_device_type()
    await relay.get_device_id()

    await relay.set_device_name('n')
    await relay.set_device_channel('c')

    await relay.set_led_on('00FF00')
    await relay.set_single_led_on(3, '00FF00')
    await relay.set_led_rainbow()
    await relay.set_led_rainbow(5)
    await relay.set_led_flash('00FF00')
    await relay.set_led_flash('00FF00', 5)
    await relay.set_led_breathe('00FF00')
    await relay.set_led_breathe('00FF00', 5)
    await relay.set_led_rotate('00FF00')
    await relay.set_led_rotate('00FF00', 5)
    await relay.set_led_off()

    await relay.vibrate()
    await relay.vibrate([100, 200, 300])

    await relay.start_timer(10)
    await relay.stop_timer()

    incident_id = await relay.create_incident('i')
    await relay.resolve_incident(incident_id, 'r')

    await relay.restart_device()

    await relay.power_down_device()

    await relay.stop_playback('1839')
    await relay.stop_playback(['1839', '1840', '1850', '1860'])
    await relay.stop_playback()

    await relay.terminate()


@wf.on_button(button='action', taps='single')
async def handle_action_single_tap(relay, button, taps):
    # button: action, channel
    # taps: single, double, triple
    await relay.say(f'{inspect.currentframe().f_code.co_name}({button}, {taps})')


@wf.on_button(button='action')
async def handle_action(relay, button, taps):
    await relay.say(f'{inspect.currentframe().f_code.co_name}({button}, {taps})')


@wf.on_button(taps='double')
async def handle_double_tap(relay, button, taps):
    await relay.say(f'{inspect.currentframe().f_code.co_name}({button}, {taps})')


@wf.on_button
async def handle_button(relay, button, taps):
    await relay.say(f'{inspect.currentframe().f_code.co_name}({button}, {taps})')


@wf.on_notification
async def handle_notification(relay, source, event, name, state):
    await relay.say(f'{inspect.currentframe().f_code.co_name}({source}, {event}, {name}, {state})')


@wf.on_timer
async def handle_timer(relay):
    await relay.say(f'{inspect.currentframe().f_code.co_name}()')


