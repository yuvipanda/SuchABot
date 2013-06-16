import os
import logging

import paramiko
import redis
import yaml

CONFIG_FILE = os.path.expanduser('~/.suchabot.yaml')
with open(CONFIG_FILE) as f:
    config = yaml.load(f)

SERVER = config['gerrit']['server']
USER = config['gerrit']['username']
PORT = config['gerrit']['port']

REDIS_DB = config['redis']['db']
REDIS_HOST = config['redis']['host']
PREFIX = config['stream_receiver']['redis_prefix']
CLIENTS_KEY = config['stream_receiver']['clients_key']

logging.basicConfig(format='%(asctime)s %(message)s', filename=os.path.expanduser('~/logs/stream-receiver'), level=logging.INFO)

ssh = paramiko.SSHClient()
ssh.load_system_host_keys()
logging.info('Attempting SSH conncetion to %s', SERVER)
ssh.connect(SERVER, username=USER, port=PORT)
logging.info('SSH connection to %s succeeded', SERVER)

logging.info('Attempting to Redis connection to %s', REDIS_HOST)
red = redis.StrictRedis(host=REDIS_HOST, db=REDIS_DB)
logging.info('Redis connection to %s succeded', REDIS_HOST)

with open('publish-clients.lua') as f:
    publish_clients = red.register_script(f.read())

def make_key(*key_parts):
    return PREFIX + "_" + '.'.join(key_parts)

if __name__ == '__main__':
    stdin, stdout, stderr = ssh.exec_command('gerrit stream-events')
    line = stdout.readline()
    while line:
        count = publish_clients(keys=[make_key(CLIENTS_KEY)], args=[line])
        logging.info('Pushed to %s clients', count)
        line = stdout.readline()
    stdout.close()
