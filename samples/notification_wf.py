#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    text = await relay.get_var('text')
    target = await relay.get_var('targets')
    ntype = await relay.get_var('type')

    if ntype == 'broadcast':
        await relay.broadcast(text, target)

    elif ntype == 'notify':
        await relay.notify(text, target)

    elif ntype == 'alert':
        await relay.notify(text, target)

@wf.on_notification(event='ack_event')
async def ack_handler(relay, source, event):
    await relay.say(f'ack ack baby ! {source} acknowledged the alert')
    await relay.terminate()

