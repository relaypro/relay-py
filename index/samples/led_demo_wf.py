#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)


@wf.on_start
async def start_handler(relay):
    await relay.set_var('effect_num', '0')
    await relay.say('To see the next effect, tap the talk button. Double tap at any time to end the demo.')

@wf.on_button(button='action', taps='single')
async def demo_handler(relay, button, taps):
    num = int(await relay.get_var('effect_num'))
    await relay.set_var('effect_num', str(num+1))
    await effects[num](relay)

@wf.on_button(button='action', taps='double')
async def stop_handler(relay, button, taps):
    await off(relay)

async def rainbow(relay):
    await relay.say('first up is the rainbow effect')
    await relay.set_led_rainbow()

async def rotate(relay):
    await relay.say('rotate effect')
    await relay.set_led_rotate('FF0000')

async def flash(relay):
    await relay.say('flash effect')
    await relay.set_led_flash('00FF00')

async def breathe(relay):
    await relay.say('breathe effect')
    await relay.set_led_breathe('0000FF')

async def on(relay):
    await relay.say('setting leds to green')
    await relay.set_led_on('00FF00')

async def off(relay):
    await relay.say('switching all leds off')
    await relay.set_led_off()
    await relay.say('stopping led demo')
    await relay.terminate()

effects = [rainbow, rotate, flash, breathe, on, off]

