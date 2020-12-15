#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    text = await relay.get_var('text')
    targets = (await relay.get_var('targets')).split(',')
    ntype = await relay.get_var('type')

    if ntype == 'broadcast':
        await relay.broadcast(text, targets)
        await relay.terminate()

    elif ntype == 'notify':
        await relay.notify(text, targets)

    elif ntype == 'alert':
        await relay.alert(text, targets)

@wf.on_notification(event='ack_event')
async def ack_handler(relay, source, event):
    await relay.say(f'ack ack baby ! {source} acknowledged the alert')
    await relay.terminate()

