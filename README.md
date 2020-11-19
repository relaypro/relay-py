# relay-py

Draft of a Python SDK for Relay Workflows.

## Installation

Install into a virtual environment (Python 3.6.1+).

```bash
pip install git+ssh://git@bitbucket.org/republicwireless/relay-py.git#egg=relay-py
```

## Usage

```python
#!/usr/bin/env python

import asyncio
import relay.workflow

wf = relay.workflow.Workflow('localhost', 8765)

@wf.on_start
async def start_handler(relay):
    greeting = await relay.get_var('greeting')
    name = await relay.get_device_name()
    await relay.say('What is your name?')
    user = await relay.listen([])
    await relay.say(f'Hello {user}! {greeting} {name}')
    await relay.terminate()


@wf.on_button
async def handle_button(relay, button, taps):
    # button: action, channel
    # taps: single, double, triple
    await relay.say('Please say your name while holding the button down.')


@wf.on_notification
async def handle_notification(relay, source, event):
    await relay.say(f'Received notification {event} from {source}')


@wf.on_timer
async def handle_timer(relay):
    await relay.say('Received timer event')


asyncio.get_event_loop().run_forever()
```

## Development

```bash
git clone git@bitbucket.org:republicwireless/relay_py.git
cd relay_py
virtualenv venv
. venv/bin/activate
pip install -e .
```

Run an example:
in terminal 1...
```bash
cd relay_py
. venv/bin/activate
cd samples
python hello_world.py
```

in terminal 2...
```bash
cd relay_py
. venv/bin/activate
python tests/hello_world_test.py
```

expected output in terminal 2...
```
> {"_type": "wf_api_start_event"}
< {"_type": "wf_api_get_var_request", "name": "greeting", "_id": "1e26dbd0df5f4492b1196751735accd8"}
> {"_id": "1e26dbd0df5f4492b1196751735accd8", "_type": "wf_api_get_var_response", "value": "Welcome"}
< {"_type": "wf_api_get_device_info_request", "query": "name", "refresh": false, "_id": "58596106a8ee4d7da77d471961470150"}
> {"_id": "58596106a8ee4d7da77d471961470150", "_type": "wf_api_get_device_info_response", "name": "device 1"}
< {"_type": "wf_api_say_request", "text": "What is your name?", "_id": "b769eb99497b42dabeba2e89a183a3ab"}
< {"_type": "wf_api_listen_request", "phrases": [], "transcribe": true, "timeout": 60, "_id": "866e7bb23e784a90bafd3c96693d50f0"}
> {"_id": "866e7bb23e784a90bafd3c96693d50f0", "_type": "wf_api_listen_response", "text": "Bob"}
< {"_type": "wf_api_say_request", "text": "Hello Bob! Welcome device 1", "_id": "7d37e1c9087949d2b2457b3c37607e6a"}
< {"_type": "wf_api_terminate_request", "_id": "ca68ef4a3ad744a696f8ba4d7988c453"}
```


## License
[MIT](https://choosealicense.com/licenses/mit/)

