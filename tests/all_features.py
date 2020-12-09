#!/usr/bin/env python

import inspect

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

    await relay.get_device_name()
    await relay.get_device_location()
    await relay.get_device_indoor_location()
    await relay.get_device_battery()

    await relay.set_device_name('n')
    await relay.set_device_channel('c')

    await relay.set_led_on('00FF00')
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

    await relay.create_incident('i')
    await relay.resolve_incident()

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
async def handle_notification(relay, source, event):
    await relay.say(f'{inspect.currentframe().f_code.co_name}({source}, {event})')


@wf.on_timer
async def handle_timer(relay):
    await relay.say(f'{inspect.currentframe().f_code.co_name}()')

