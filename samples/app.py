
# Copyright © 2022 Relay Inc.

import logging
import logging.config
import yaml

with open('logging.yml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)


import relay.workflow

# import deviceinfo_demo_wf as deviceinfo
# import interval_timer_wf as timer
# import led_demo_wf as led
# import login_wf as login
# import notification_wf as notification
# import panic_wf as panic
# import transcribe_wf as transcribe
# import vibrate_demo_wf as vibrate
# import broadcast as broadcast

def main():
    server = relay.workflow.Server('localhost', 8080)

    # server.register(deviceinfo.wf, '/deviceinfo')
    # server.register(broadcast.wf, '/broadcast')
    # server.register(timer.wf, '/timer')
    # server.register(led.wf, '/led')
    # server.register(login.wf, '/login')
    # server.register(notification.wf, '/notification')
    # server.register(panic.wf, '/panic')
    # server.register(transcribe.wf, '/transcribe')
    # server.register(vibrate.wf, '/vibrate')

    server.start()
    

if __name__ == "__main__":
    main()

