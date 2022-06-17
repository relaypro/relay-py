#!/usr/bin/python3

# Copyright © 2022 Relay Inc.

# add one workflow:
# $ user_id=123 gen_wf.py <yml file> | r_wh -d @-
#
# add all workflows:
# export user_id=123
# $ ls *_wf.yml | xargs -I% bash -c './gen_wf.py % | curl -s -H "authorization: Bearer $token" "https://$ibot/ibot/workflow?subscriber_id=$subscriber_id" -d @-'

import argparse
import json
import os


def get_name(n, f):
    default_names = {
        'deviceinfo_demo_wf.yml' : 'device info workflow',
        'hello_world_wf.yml'     : 'hello workflow',
        'interval_timer_wf.yml'  : 'timer workflow',
        'led_demo_wf.yml'        : 'light workflow',
        'login_wf.yml'           : 'login workflow',
        'notification_wf.yml'    : 'notification workflow',
        'panic_wf.yml'           : 'panic workflow',
        'transcribe_wf.yml'      : 'transcribe workflow',
        'vibrate_demo_wf.yml'    : 'vibrate workflow'}

    return n if n else default_names[f]

def flatten(f):
    with open(f, 'r') as fp:
        return '\n'.join(fp.read().splitlines())


parser = argparse.ArgumentParser()
parser.add_argument('-n', '--name', default=None)
parser.add_argument('-d', '--device_ids', default=os.environ['user_id'], help='comma-delimited list of device_ids')
parser.add_argument('config_file')

args = parser.parse_args()


reg = {
    'name': get_name(args.name, args.config_file),
    'install': args.device_ids.split(','),
    'config': flatten(args.config_file)
}

print(json.dumps(reg))

