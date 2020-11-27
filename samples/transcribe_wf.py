#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    await listen()

async def listen():
    await relay.say('speak your sentence')
    text = await relay.listen()
    await relay.say(f'transcribed text is {text}')
    await relay.say('tap the talk button for another transcription')

@wf.on_button(button='action', taps='single')
async def tap_handler(relay, button, taps):
    await listen()

@wf.on_button(button='action', taps='double')
async def double_tap_handler(relay, button, taps):
    await relay.say('stopping transcribe workflow')
    await relay.terminate()

