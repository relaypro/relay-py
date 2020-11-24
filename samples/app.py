import logging
import logging.config
import yaml

import relay.workflow
import all_features


with open('logging.yml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)


def main():
    server = relay.workflow.Server('localhost', 8765)
    server.register(all_features.wf, '/hello')
    server.start()
    

if __name__ == "__main__":
    main()


