#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    itype = await relay.get_var('incident_type', 'demo')
    await relay.create_incident('itype')
    await relay.say('created an incident')
    #await relay.resolve_incident()
    await relay.terminate()

