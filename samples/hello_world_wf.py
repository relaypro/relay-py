#!/usr/bin/env python3

# Copyright © 2022 Relay Inc.

import relay.workflow
import os
import logging

logging.basicConfig()
port = os.getenv('PORT', 8080)
wf_server = relay.workflow.Server('0.0.0.0', port, log_level=logging.INFO)
hello_workflow = relay.workflow.Workflow('hello workflow')
wf_server.register(hello_workflow, '/hellopath')

interaction_name = 'hello interaction'


@hello_workflow.on_start
async def start_handler(workflow, trigger):
    target = workflow.make_target_uris(trigger)
    await workflow.start_interaction(target, interaction_name)


@hello_workflow.on_interaction_lifecycle
async def lifecycle_handler(workflow, itype, interaction_uri, reason):
    if itype == relay.workflow.TYPE_STARTED:
        await workflow.say_and_wait(interaction_uri, 'hello world')
        await workflow.end_interaction(interaction_uri, interaction_name)
    if itype == relay.workflow.TYPE_ENDED:
        await workflow.terminate()


wf_server.start()
