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

wf = relay.workflow.Workflow('hello')

@wf.on_start
async def start_handler(relay):
    greeting = await relay.get_var('greeting')
    label = await relay.get_device_label()
    await relay.say('What is your name?')
    user = await relay.listen([])
    await relay.say(f'Hello {user}! {greeting} {label}')
    await relay.terminate()

server = relay.workflow.Server('localhost', 8765)
server.register(wf, '/hello')
server.start()
```

## Development

```bash
git clone git@bitbucket.org:republicwireless/relay_py.git
cd relay_py
virtualenv venv
. venv/bin/activate
pip install -e .
```

Start demo workflow server:
```bash
cd relay_py
. venv/bin/activate
cd samples
python app.py
```

Run tests:
```bash
cd relay_py
. venv/bin/activate
pip install -e .[testing]
pytest
```

## License
[MIT](https://choosealicense.com/licenses/mit/)

