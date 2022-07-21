# relay-py

A Python SDK for [Relay Workflows](https://developer.relaypro.com).

## Installation

Install into a virtual environment (Python 3.6.1+).

    python3 -m venv venv
    . venv/bin/activate
    pip3 install git+ssh://git@github.com/relaypro/relay-py.git#egg=relay-py
    cd relay-py
    pip3 install -e .

## Usage

- The following demonstrates a simple Hello World program, located in the `hello_world_wf.py` file:
<pre>
    #!/usr/bin/env python3

    import asyncio
    import os
    import relay.workflow
    import logging
    import time

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    wf = relay.workflow.Workflow('hello')
    port = os.getenv('PORT')
    if port is None:
        port = 8080

    @wf.on_start
    async def start_handler(relay, trigger):

        device_urn = trigger['args']['source_uri']
        target = relay.make_target_uris(trigger)

        await relay.start_interaction(target, 'hello world')


    @wf.on_interaction_lifecycle
    async def lifecycle_handler(relay, itype, interaction_uri, reason):
        if itype == 'started':
            device_name = await relay.get_device_name(interaction_uri)
            await relay.say_and_wait(interaction_uri, 'What is your name?')
            user_provided_name = await relay.listen(interaction_uri, 'request1')
            greeting = await relay.get_var('greeting')
            await relay.say_and_wait(interaction_uri, f'{greeting} {user_provided_name}! You are currently using {device_name}')
            await relay.end_interaction(interaction_uri, 'hello world')
        if itype == 'ended':
            await relay.terminate()

    @wf.on_stop
    async def stop_handler(relay, reason):
        logger.debug(f'stopped: {reason}')

    @wf.on_prompt
    async def prompt_handler(relay, source_uri, type):
        logger.debug(f'source uri: {source_uri}, type: {type}')
</pre>

## Development

    bash
    git clone git@github.com:relaypro/relay-py.git
    cd relay-py
    virtualenv venv
    . venv/bin/activate
    pip3 install -e .

Start demo workflow server:

    bash
    cd relay-py
    . venv/bin/activate
    cd samples
    python3 app.py

Run tests:

    bash
    cd relay-py
    . venv/bin/activate
    pip3 install -e .[testing]
    pytest


## Deployment on ngrok

- Install ngrok on your machine by creating an account and downloading from
`https://dashboard.ngrok.com/get-started/setup`, or entering the
command `npm install -g ngrok` into your shell. Once you have ngrok installed, expose your 
workflow to the internet by entering the following command (assuming your workflow listens on
port 8080 locally):

<pre>
    ngrok http 8080
</pre>

- Run the ngrok http command in a different shell window than the one where you will be running your code, so that you can keep ngrok running while you edit and run your workflows.  After typing in the command, you will see information about your session including an https forwarding address.   It should look like the following:

<pre>
    ngrok                         (Ctrl+C to quit)

    Session Status                online
    Account                       Relay User (Plan: Free)
    Version                       3.0.6
    Region                        United States (us)
    Latency                       29ms
    Web Interface                 http://127.0.0.1:4040
    Forwarding                    https://8adb-8-48-95-57.ngrok.io -> http://localhost:8080

    Connections                   ttl     opn     rt1     rt5     p50     p90
                                  0       0       0.00    0.00    0.00    0.00
</pre>

- Now start your workflow:

<pre>$ python3 mywf.py</pre>

- When registering a workflow, you would use the Forwarding URL provided by ngrok, but replacing the `https` protocol with `wss`, and appending the path that you use in the `register` method call in your workflow:

<pre>
relay workflow:create:phrase -n hellophrase -u 'wss://8adb-8-48-95-57.ngrok.io/hellopath' --trigger hello -i 990007560012345
</pre>

- As you make iterative changes to your workflow, you'll need to stop and restart the `mywf.py` script for source changes to take effect, but can leave the ngrok executable running.

## Deployment on Heroku

- Because Heroku chooses the local port for you and passes that
configuration to your script using the PORT environment variable,
change the host and port for relay.workflow.Server in your workflow
code to this:

<pre>
    port = os.getenv('PORT')
    if port is None:
        port = 8080
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


## Deployment on AWS EC2

- get an SSL certificate keypair for your server. This is because you must use
the secure websocket protocol ("wss") in the URI when registering a workflow with
the Relay server. This means that your EC2 server will need to have an HTTPS
endpoint with a certificate signed by a publicly-recognized CA (certificate
authority).
  -  One potential source is [Let's Encrypt](letsencrypt.org).
    - Be aware that Let's Encrypt has a
      [policy](https://community.letsencrypt.org/t/policy-forbids-issuing-for-name-on-amazon-ec2-domain/12692)
      against issuing certificates for hosts in the amazonaws.com DNS domain. So if
      you want to use Let's Encrypt, the FQDN for your EC2 instance will need
      to be referred to by another DNS domain.
      This can be done in AWS via a Route53 public hosted zone, or a domain
      hosted external to AWS to which you can add th IP address of your EC2
      instance.
    - If you add a new subdomain, it may take some time for propogation through
      the DNS system so that the new subdomain is resolvable by the Let's Encrypt
      servers. In the meantime, the Let's Encrypt CLI may return a SERVFAIL when
      trying to access your server hostname.
    - Let's Encrypt tool needs inbound access to port 80 of your EC2 instance
      for ownership verification, which is not enabled by default, so you will
      need to add that in the EC2 Security Group.
    - If you use the `--standalone` option with the certbot tool, you don't
      need to have an existing web server on this EC2 instance.
    - The Let's Encrypt CLI will store the key and certificate in
      /etc/letsencrypt/live/HOSTNAME/, so verify that your workflow app has
      read access to these files, which is not the default.

- open the desired inbound port in the EC2 Security Group for your workflow
application (i.e., 3000)

- configure the WebSocket server for SSL: *********** TODO add those steps here.
    `openssl s_client -debug myserver.mydomain.com:3000`

- login to the EC2 server and start the workflow application. The logs should
appear in your remote shell session.
- change the host and port for relay.workflow.Server in your workflow code to this:

<pre>
    port = 3000
    print(f'listening on port {port}')
    server = relay.workflow.Server('0.0.0.0', port)
</pre>

- copy all the files needed for your workflow application to the EC2 server

    `$ scp -r myapp ubuntu@ec2-54-123-45-67.compute-1.amazonws.com:`


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
    along with mapping to port 443. You do NOT need to get your own HTTPS
    certificate.
  - AWS EC2 does not provide HTTPS automatically. One way to get HTTPS on
    EC2 is to obtain a key/certificate pair signed by a publicly-recognized
    CA (certificate authority), and use that when invoking the server.
    The Relay server does not accept self-signed certificates from the
    workflow application server.

- `$ relay whoami`<br>
get the subscriber ID from the "Default Subscriber" column.

- `$ relay workflow:create:phrase -n pythonphrase -u wss://ec2-54-123-45-67.compute-1.amazonws.com:3000/hellopath --trigger="python" --install=990007560023456`

- If you get the error 'missing_capability' then contact Relay Support to
get your account updated so workflows can be registered on it.


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

