import logging
import logging.config
import yaml

with open('logging.yml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)


import asyncio
from concurrent.futures import as_completed
from flask import Flask, request
import relay.workflow
import threading


# Flask setup
app = Flask(__name__)

@app.route('/webhook/broadcast', methods=['POST'])
def handle_webhook_broadcast():
    message = request.json['message']

    # returns [concurrent.futures.Future]
    futures = [asyncio.run_coroutine_threadsafe(relay.say(message), wf_event_loop) for relay in relays.copy()]
    for future in as_completed(futures, 1):
        try:
            future.result()
        except asyncio.TimeoutError:
            future.cancel()
        except Exception as x:
            print(f'exception: {x}')

    return ('', 202)


# Relay workflow setup
wf = relay.workflow.Workflow('wf')

# Maintain a set of handles for connected Relays; handles can be used for async signaling.
# The websocket "closed" event is hooked below to discard closed handles.
relays = set()

@wf.on_start
async def start_handler(relay):
    relays.add(relay)

    await relay.listen(['disconnect'])
    await relay.terminate()

@wf.on_end
async def end_handler(relay):
    relays.discard(relay)


# workflow websocket server will be launched on a separate thread
wf_event_loop = asyncio.new_event_loop()

def start_websocket():
    def start_ws(loop):
        asyncio.set_event_loop(loop)

        server = relay.workflow.Server('localhost', 8765)
        server.register(wf, '/connect')
        server.start()

    t = threading.Thread(target=start_ws, args=(wf_event_loop,), daemon=True)
    t.start()

start_websocket()

