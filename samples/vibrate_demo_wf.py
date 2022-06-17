#!/usr/bin/env python

# Copyright © 2022 Relay Inc.

import relay.workflow

wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    await relay.say('this is a default vibrate pattern')
    await relay.vibrate()
    await relay.terminate()

