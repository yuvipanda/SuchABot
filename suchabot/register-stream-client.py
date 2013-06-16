import sys
import os
import logging

import redis
import yaml


CONFIG_FILE = os.path.expanduser('~/.suchabot.yaml')
with open(CONFIG_FILE) as f:
    config = yaml.load(f)

REDIS_DB = config['redis']['db']
REDIS_HOST = config['redis']['host']
PREFIX = config['stream_receiver']['redis_prefix']
CLIENTS_KEY = config['stream_receiver']['clients_key']

logging.basicConfig(format='%(asctime)s %(message)s', filename=os.path.expanduser('~/logs/register-stream-client'), level=logging.INFO)

logging.info('Attempting to Redis connection to %s', REDIS_HOST)
red = redis.StrictRedis(host=REDIS_HOST, db=REDIS_DB)
logging.info('Redis connection to %s succeded', REDIS_HOST)

def make_key(*key_parts):
    return PREFIX + "_" + '.'.join(key_parts)

if __name__ == '__main__':
    new_client_key = sys.argv[1]
    red.sadd(make_key(CLIENTS_KEY), new_client_key)
    red.save() # We don't want to lose client lists do we
    logging.info('Added key %s' % new_client_key)
