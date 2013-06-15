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
REDIS_EXPIRE = config['redis']['key_timeout']
PREFIX = config['redis']['prefix']

logging.basicConfig(format='%(asctime)s %(message)s', filename=os.path.expanduser('~/logs/stream-receiver'), level=logging.INFO)

ssh = paramiko.SSHClient()
ssh.load_system_host_keys()
logging.info('Attempting SSH conncetion to %s', SERVER)
ssh.connect(SERVER, username=USER, port=PORT)
logging.info('SSH connection to %s succeeded', SERVER)

logging.info('Attempting to Redis connection to %s', REDIS_HOST)
red = redis.StrictRedis(host=REDIS_HOST, db=REDIS_DB)
logging.info('Redis connection to %s succeded', REDIS_HOST)

def make_key(*key_parts):
    return PREFIX + "_" + '.'.join(key_parts)

def get_next_id():
    return red.incr(make_key('nextid'))

if __name__ == '__main__':
    stdin, stdout, stderr = ssh.exec_command('gerrit stream-events')
    line = stdout.readline()
    while line:
        id = unicode(get_next_id())
        key = make_key(u'message', id)
        red.setex(key, REDIS_EXPIRE, line)
        logging.info('Pushed key %s', key)
        line = stdout.readline()
    stdout.close()
