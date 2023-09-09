# relay-py

A Python SDK for [Relay Workflows](https://developer.relaypro.com).

## Guides Documentation

The higher-level guides are available at https://developer.relaypro.com/docs

## API Reference Documentation

The generated pydoc documentation is available at https://relaypro.github.io/relay-py/

## Installation

Install into a virtual environment (Python 3.6.1+).

    $ python3 -m venv venv
    $ . venv/bin/activate
    (venv)$ pip install --upgrade pip
    (venv)$ pip install git+https://git@github.com/relaypro/relay-py.git#egg=relay-py

## Usage

- The following demonstrates a simple Hello World program, located in the `samples/hello_world_wf.py` file:
<pre>
import relay.workflow
import os
import logging

port = os.getenv('PORT', 8080)
wf_server = relay.workflow.Server('0.0.0.0', port, log_level=logging.INFO)
hello_workflow = relay.workflow.Workflow('hello workflow')
wf_server.register(hello_workflow, '/hellopath')


@hello_workflow.on_start
async def start_handler(workflow, trigger):
    target = workflow.make_target_uris(trigger)
    await workflow.start_interaction(target, "interaction name")


@hello_workflow.on_interaction_lifecycle
async def lifecycle_handler(workflow, itype, interaction_uri, reason):
    if itype == relay.workflow.TYPE_STARTED:
        await workflow.say_and_wait(interaction_uri, 'hello world')
        await workflow.end_interaction(interaction_uri)
    if itype == relay.workflow.TYPE_ENDED:
        await workflow.terminate()


wf_server.start()
</pre>

## Development

Setup:

    $ git clone git@github.com:relaypro/relay-py.git
    $ cd relay-py
    $ python3 -m venv venv
    $ . venv/bin/activate
    (venv)$ pip install --upgrade pip
    (venv)$ pip install --editable .

Start demo workflow server (after setup):

    (venv)$ cd samples
    (venv)$ python hello_world_wf.py

If your workflow process ends very shortly after starting and without any
error messages, check that your workflow didn't forget to invoke
`relay.workflow.Server.start()`.

Run tests (after setup):

    # start inside the relay-py directory
    (venv)$ pip install --editable '.[testing]'
    (venv)$ pytest

Build docs (locally):
    # start inside the relay-py directory
    (venv)$ pip install --editable '.[docs]'
    (venv)$ mkdocs serve
    # open browser to http://127.0.0.1:8000
    # ctrl-c to quit local doc server

## Additional Instructions for Deployment on Heroku

See the [Guide](https://developer.relaypro.com/docs/heroku).

Here are some instructions specific to Python:

- Because Heroku chooses the local port for you and passes that
configuration to your script using the PORT environment variable,
you should have something like the following code:

<pre>
port = os.getenv('PORT', 8080)
wf_server = relay.workflow.Server('0.0.0.0', port)
</pre>

- identify the name of your workflow's python script that you wrote. In this
example we'll call it `hellow_world_wf.py`.

- create the file `Procfile` in the top directory of your Heroku project,
with the following contents that describe how to start your application
(the "web" keyword is special in Heroku):

    `web: python hello_world_wf.py`

- create the file `requirements.txt` in the top directory of your Heroku
  project, with the following 2 lines as contents:

<pre>
    websockets
    requests
    pyyaml
</pre>

- create the file `runtime.txt` in the top directory of your Heroku project,
  with the following 1 line as contents, depending on your preferred version of python
  (it needs to be at least 3.6 to meet Relay Python SDK requirements):

    `python-3.10.4`

## Verbose Mode Logging

By default, the Relay Python SDK will log WARNING level and higher to the
console. If you wish to log more or less information from the SDK, use the
`log_level` kwarg on the `Server` constructor, like this:

`wf_server = relay.workflow.Server('0.0.0.0', port, log_level=logging.DEBUG)`

The `Server` constructor also supports the `log_handler` kwarg where you
can pass in a handler object from the `logging.handlers` module. Since
there are no handlers in the SDK by default, the default behavior for any
logging is to print it to the console. For example:

`wf_server = relay.workflow.Server('0.0.0.0', port, log_level=logging.DEBUG, log_handler=logging.handlers.SysLogHandler())`

## TLS Capability

Your workflow server must be exposed to the Relay server with TLS so
that the `wss` (WebSocket Secure) protocol is used, this is enforced by
the Relay server when registering workflows. See the
[Guide](https://developer.relaypro.com/docs/requirements) on this topic.

There are multiple ways to provide a TLS endpoint, such as a reverse proxy
found in ngrok or Heroku or an Application Load Balancer, or directly in
the Python websocket server.

The websocket server that is built-in to this Python Relay SDK has support
for providing TLS encryption, given that you have a TLS key and certificate.
For example, you can get a TLS key and certificate from letsencrypt.org. Or
you can use a commercial provider. Sometimes this key and certificate for
HTTP-over-TLS is called an "SSL certificate".

To use the built-in TLS support, the key and certificate both need to
be in PEM format, and in a file that can be read locally by the workflow
process.

When you want to use the built-in TLS support, you supply keyword arguments
to this function that identify the filename of both the key and the
certificate, for example:

    my_ssl_key_filename = '/etc/letsencrypt/live/myserver.mydomain.com/privkey.pem'
    my_ssl_cert_filename = '/etc/letsencrypt/live/myserver.mydomain.com/fullchain.pem'
    server = relay.workflow.Server('0.0.0.0', 443, ssl_key_filename=my_ssl_key_filename, ssl_cert_filename=my_ssl_cert_filename)

Now when you start your workflow application, in the log you should see this line:

`Relay workflow server (relay-sdk-python/2.0.0) listening on 0.0.0.0 port 443 with ssl_context MySslContext`

When it says "ssl_context" instead of "plaintext", that is the clue that TLS is enabled.

If you want to verify the certificate that your server is presenting to web clients, run:

`openssl s_client -debug myserver.mydomain.com:443`

## License
[MIT](https://choosealicense.com/licenses/mit/)

