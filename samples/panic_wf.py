#!/usr/bin/env python

import relay.workflow


wf = relay.workflow.Workflow(__name__)

@wf.on_start
async def start_handler(relay):
    itype = await relay.get_var('incident_type', 'Panic Alert')
    targets = (await relay.get_var('targets')).split(',')

    await relay.create_incident(itype)

    address = await relay.get_device_address()
    label = await relay.get_device_label()

    await relay.alert(f'alert for {label} at {address}', targets, name='initial_alert')

    confirm = await relay.get_var('audible_confirmation_for_originator', 'true') == 'true'
    if confirm:
        await relay.say('Panic alert sent.')


@wf.on_notification(name='initial_alert', event='ack_event')
async def ack_handler(relay, source, name, event, state):
    created = state['created']
    acked = state['acknowledged']
    not_responded = [i for i in created if i not in acked]

    await relay.cancel_notification(name, not_responded)
    await relay.set_var('acknowledged_by', source)
    await relay.broadcast(f'{source} has responded to the panic alert.', not_responded)

    emergency_group = await relay.get_var('emergency_group', None)
    if emergency_group:
        await relay.set_channel(emergency_group, acked)

    confirm = await relay.get_var('audible_confirmation_for_originator', 'true') == 'true'
    if confirm:
        await relay.alert(f'alert acknowledged by {source}', [ await relay.get_device_label() ], name='acknowledge_response')

    else:
        relay.resolve_incident()
        relay.terminate()


@wf.on_notification(name='acknowledge_response', event='ack_event')
async def ack_response_handler(relay, source, name, event, state):
    acknowledged_by = await relay.get_var('acknowledged_by', 'unknown')
    await relay.resolve_incident()
    await relay.terminate()
