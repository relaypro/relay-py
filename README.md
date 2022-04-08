# relay-py

Draft of a Python SDK for Relay Workflows.

## Installation

Install into a virtual environment (Python 3.6.1+).

    python -m venv venv
    . venv/bin/activate
    pip install -e .

    pip install git@github.com:relaypro/relay-py.git#egg=relay-py

## Usage

    python
    #!/usr/bin/env python

    import asyncio
    import relay.workflow

    wf = relay.workflow.Workflow('hellowf')

    @wf.on_start
    async def start_handler(relay):
        name = await relay.get_device_name()
        await relay.say('What is your name?')
        user = await relay.listen([])
        await relay.say(f'Hello {user}! from {name}')
        await relay.terminate()

    server = relay.workflow.Server('localhost', 3000)
    server.register(wf, '/hellopath')
    server.start()

## Development

    bash
    git clone git@github.com:relaypro/relay-py.git
    cd relay_py
    virtualenv venv
    . venv/bin/activate
    pip install -e .

Start demo workflow server:

    bash
    cd relay_py
    . venv/bin/activate
    cd samples
    python app.py

Run tests:

    bash
    cd relay_py
    . venv/bin/activate
    pip install -e .[testing]
    pytest

## Deployment on ngrok

## Deployment on Heroku

- Because Heroku chooses the local port for you and passes that
configuration to your script using the PORT environment variable,
change the host and port for relay.workflow.Server in your workflow
code to this:

<pre>
    port = os.getenv('PORT')
    if port is None:
        port = 3000
    print(f'listening on port {port}')
    server = relay.workflow.Server('0.0.0.0', port)
</pre>

- identify the name of your workflow's python script that you wrote. In this
example we'll call it `mywf.py`.

- create the file `Procfile` in the top directory of your Heroku project,
with the following contents that describe how to start your application
(the "web" keyword is special in Heroku):

    `web: python mywf.py`

- create the file `requirements.txt` in the top directory of your Heroku
  project, with the following 2 lines as contents:

<pre>
    websockets
    pyyaml
</pre>

- create the file `runtime.txt` in the top directory of your Heroku project,
  with the following 1 line as contents, depending on your preferred version of python
  (it needs to be at least 3.6 to meet Relay SDK requirements):

    `python-3.10.4`

- start displaying the server logs using the Heroku CLI:

    `$ heroku logs --tail`

- make sure the above files are committed to your Heroku git repository, then
push that git repository up to Heroku so it gets built and deployed there.
Heroku requires that the branch name be "main" or "master", otherwise the
push will not get built and deployed there after the git server receives it.
In the git push response, you should see the URL of your app:

    `remote: https://remarkable-relay-12345.herokuapp.com/ deployed to Heroku`

- You can also see the name of the app using the `heroku config` or
`heroku releases` CLI commands, in case the git push response has scrolled
off your screen:

    `=== remarkable-relay-12345 Config Vars`

- from a web browser, hit the URL of your Heroku server with https on port 443
(Heroku adds a reverse proxy automatically to your web app to provide https
capability and have it be reachable externally on port 443)

    `https://remarkable-relay-12345.herokuapp.com/hellopath`

  and if properly configured, the browser should show a message like this one from Chrome:

<pre>
    Failed to open a WebSocket connection: invalid Connection header: keep-alive.
    You cannot access a WebSocket server directly with a browser. You need a WebSocket client.
</pre>

- in the log, you should see status=101:

    `2022-03-30T20:54:25.246876+00:00 heroku[router]: at=info method=GET path="/hellopath" host=remarkable-relay-12345.herokuapp.com request_id=b6e340f3-2c59-4acc-9da5-b12dcf11fb07 fwd="52.1.25.164" dyno=web.1 connect=0ms service=2ms status=101 bytes=203 protocol=https`

  If instead in the log you see a 50x error saying "No web processes running" like this:

    `2022-03-30T19:36:12.155629+00:00 heroku[router]: at=error code=H14 desc="No web processes running" method=GET path="/" host=remarkable-relay-12345.herokuapp.com request_id=12cc47a5-5d1d-4e18-b6f3-7cef784e56f6 fwd="8.48.63.104" dyno= connect= service= status=503 bytes= protocol=https`

  then you need to start the web process with the Heroku CLI:

    `$ heroku ps:scale web=1`

- Also do a `heroku ps` CLI command and verify that your dyno is up and
not sleeping. The reason for this check is because the dyno can take
4-6 seconds to wake up from sleep, which may be a timeout for
the Relay server. For example, compare the "up" case to the "idle" case:

<pre>
    === web (Free): python mywf.py (1)
    web.1: up 2022/03/30 17:42:09 -0400 (~ 1m ago)

    === web (Free): python mywf.py (1)
    web.1: idle 2022/03/31 14:42:07 -0400 (~ 1m ago)
</pre>

If your dyno is idle, hit the URL with a web browser to wake it up. It will
go idle again in a few minutes of non-use.

## Registration on Heroku

Use the Relay CLI to register your workflow application with the Relay server.

- `$ relay whoami`<br>
get the subscriber ID from the "Default Subscriber" column.

- `$ relay workflow:create:phrase -n pythonphrase -u wss://remarkable-relay-12345.herokuapp.com/hellopath --trigger="python" --install=990007560023456`

- If you get the error `missing_capability` then contact Relay Support to
get your account updated so it can be modified to allow for workflows.
In the `workflow:create` command note the use of the wss (web socket
secure) protocol and the default port 443 in the URI for that protocol, as
the Heroku infrastructure automatically provides a HTTPS endpoint on port
443 in front of your application server.

- `$ relay workflow:list -x`<br>
get the workflow ID from the "ID" column.

- `$ relay devices`<br>
get the list of all the device IDs on your account. Pick
one for the install command as follows. If you need help figuring out the ID
of a named device, go into Dash in Account -> Users.

- `$ relay workflow:install -w wf_pythonphrase_bN8RoR9BpGK41urSjGUdjsC -s ed2a4a98-0395-4612-8f60-bd1234567890 990007560123456`

## Deployment on AWS EC2

- see the bullet below in the Registration section.  You must use the secure
websocket protocol ("wss") in the URI when registering a workflow with the Relay
server. This means that your AWS server will need to have an https endpoint with
a certificate signed by a publicly-recognized CA (certificate authority).
FYI in case this point steers you away from AWS EC2.

- change the host and port for relay.workflow.Server in your workflow code to this:

<pre>
    port = 3000
    print(f'listening on port {port}')
    server = relay.workflow.Server('0.0.0.0', port)
</pre>

- copy all the files needed for your workflow application to the EC2 server

    `$ scp -r myapp ubuntu@ec2-54-123-45-67.compute-1.amazonws.com:`

- get an SSL certificate keypair for your server.
  -  One potential source is [Let's Encrypt](letsencrypt.org).  However,
     Let's Encrypt has a
     [policy](https://community.letsencrypt.org/t/policy-forbids-issuing-for-name-on-amazon-ec2-domain/12692)
     against issuing certificates for hosts in the amazonaws.com domain. So if
     you want to use Let's Encrypt, you will need to use another DNS domain
     (if you already have a domain, even if that domain is hosted outside AWS,
     a new subdomain defined in AWS's Route53 as a "public hosted zone") should
     work for this without additional cost from AWS). Also note that the
     Let's Encrypt tool needs inbound access to port 80 of your EC2 instance,
     which is not enabled by default, so you will need to add that in the
     Security Group. The Let's Encrypt CLI will store the key and certificate
     in /etc/letsencrypt/live/HOSTNAME/.

- configure the WebSocket server for SSL: *********** TODO add those steps here.
    `openssl s_client -debug python.marcel.sandbox.relaydev.sh:3000`

- login to the EC2 server and start the workflow application. The logs should
appear in your remote shell session.

<pre>
    $ ssh myapp ubuntu@ec2-54-123-45-67.compute-1.amazonws.com
    $ cd myapp
    $ python3 mywf.py
</pre>

- from a web browser, hit the URL of your EC2 server (note the use of https
here because the wss protocol must be used)

    `https://ec2-54-123-45-67.compute-1.amazonws.com:3000/hellopath`

 and if properly configured, the browser should show a message like:
 (there won't be any log entries, because the websocket did not get fully established.)

<pre>
    Failed to open a WebSocket connection: invalid Connection header: keep-alive.
    You cannot access a WebSocket server directly with a browser. You need a WebSocket client.
</pre>


## Registration

Use the Relay CLI to register your workflow application with the Relay server.

- note that because unsecure websocket ("ws") is not a supported protocol by
the Relay server, you must use the secure websocket protocol ("wss") in the
URI when registering a workflow with the Relay server. 
  - Heroku will by default provide an HTTPS front end for you automatically,
    along with mapping to port 443.
  - AWS EC2 does not provide HTTPS automatically. One way to get HTTPS on
    EC2 is to obtain a key/certificate pair signed by a publicly-recognized
    CA (certificate authority), and use that when invoking the server.
    The Relay server does not accept self-signed certificates from the
    workflow application server.

- `$ relay whoami`<br>
get the subscriber ID from the "Default Subscriber" column.

- `$ relay workflow:create:phrase -n pythonphrase -u wss://ec2-54-123-45-67.compute-1.amazonws.com:3000/hellopath --trigger="python" --install=990007560023456`

- If you get the error 'missing_capability' then contact Relay Support to
get your account updated so it can be modified to allow for workflows.


Note the use of the non-secure ws (web socket) protocol and the custom
port 3000 in the URI, as AWS EC2 provides a raw machine by default without
SSL. You can pick pretty much any port number you want, as long as it matches
the port number in your workflow code as described in the first bullet.
However, running on a port number less than 1024 requires you to be logged in
to Linux as the root user.

- `$ relay workflow:list -x`<br>
get the workflow ID from the "ID" column.

- `$ relay devices`<br>
get the list of all the device IDs on your account. Pick
one for the install command as follows. If you need help figuring out the ID
of a named device, go into Dash in Account -> Users.

- `$ relay workflow:install -w wf_pythonphrase_bN8RoR9BpGK41urSjGUdjsC -s ed2a4a98-0395-4612-8f60-bd7b08d5b9a1 990007560123456`

## Invoking

Hold the Assistant button (between the volume up and volume down buttons)
on the Relay and speak the trigger phrase you specified during registration: "python".

If you hear a beep confirmation, the trigger phrase was recognized by
the server and it is going to invoke the workflow URL you specified during
registration. If instead you hear a "dum dum" error tone, then the server
did not recognize what was spoken as any trigger phrase. You can trigger
phrases for other workflows such as "time" and "battery" to check the
recognition of other built-in trigger phrases.

In the Heroku logs you should see a GET to the path your specified during
registration ("/hellopath") and any interaction you specified in your workflow
should execute.

If your workflow seems to only partially execute, tap the
assistant button on the device to see what channel it says. If the channel
name it says is the workflow name (i.e., "python") then the server is still
trying to execute your workflow. If your workflow has terminated or timed
out, it should say the channel name it was on before the workflow started.

If your workflow prompts the user for a verbal input, that workflow step will not complete
until the Relay server successfully can recognize the audio and convert
it to text. If the speech-to-text is unsuccessful, because for example
the spoken audio was unclear/indeterminate, that step will continue
to block. So the user may need to make another speaking attempt using
the action/talk button. Or your workflow may need to enforce a timeout.

To see the timing and flow of the callbacks and actions in your workflow,
enable DEBUG logging in the SDK. You can add your own log statements in
your workflow for further identification of how your workflow script
is progressing.

## License
[MIT](https://choosealicense.com/licenses/mit/)

