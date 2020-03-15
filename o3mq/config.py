import logging

import yaml

YAML_FILE = './config/O3one.yaml'

logger = logging.getLogger()


class Config:
    def __init__(self):
        self._conf = None

    def load_config(self):
        self._conf = {}

    def dump(self):
        print(self._conf)

    def set(self, key: str, value: object):
        self._conf[key.lower()] = value

    def get(self, key: str, default=None):
        if key.lower() in self._conf:
            return self._conf[key.lower()]
        return default


class YAMLConfig(Config):
    def __init__(self, config_file: str = YAML_FILE):
        super().__init__()
        self.config_file = config_file

    def load_config(self):
        try:
            with open(self.config_file, 'r') as configFile:
                self._conf = yaml.load(configFile, Loader=yaml.SafeLoader)
                logger.info(f"Loaded config from {self.config_file}.")
        except Exception as e:
            logger.error(e)

    def save(self):
        try:
            with open(self.config_file, 'w') as configFile:
                self._conf = yaml.dump(self._conf, configFile)
                logger.info(f"Saved YAML config to {self.config_file}.")
        except Exception as e:
            logger.error(e)


instance = Config()
instance.load_config()

DEFAULT_CONNECT_TIMEOUT = instance.get('DEFAULT_CONNECT_TIMEOUT', 5)
PERSIST_ENABLED = instance.get('PERSIST_ENABLED', True)
ACK_REP = instance.get('ACK_REP', "OK")
PORT_PUB = instance.get('PORT_PUB', 5555)
PORT_SUB = instance.get('PORT_SUB', 5556)
PORT_WS = instance.get('PORT_WS', 8765)
HOSTNAME = instance.get('HOSTNAME', '127.0.0.1')
LOG_PATH = instance.get('LOG_PATH', './logs/')
DB_PATH = instance.get('DB_PATH', './db/')
DASHBOARD_PORT = instance.get('DASHBOARD_PORT', 9000)
DASHBOARD_ENABLED = instance.get('DASHBOARD_ENABLED', True)
PRIORITY_ENABLED = instance.get('PRIORITY_ENABLED', False)
MMAP_ENABLED = instance.get('MMAP_ENABLED', True)
MMAP_PATH = instance.get('MMAP_PATH', './db/mapped/')
MMAP_FILE = instance.get('MMAP_FILE', 'o3.mq')


def refresh():
    global DEFAULT_CONNECT_TIMEOUT, PERSIST_ENABLED, ACK_REP, PORT_PUB, PORT_SUB, HOSTNAME, LOG_PATH, DB_PATH, \
        PORT_WS, DASHBOARD_PORT, DASHBOARD_ENABLED, PRIORITY_ENABLED, MMAP_ENABLED, MMAP_PATH, MMAP_FILE

    DEFAULT_CONNECT_TIMEOUT = instance.get('DEFAULT_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT)
    PERSIST_ENABLED = instance.get('PERSIST_ENABLED', PERSIST_ENABLED)
    ACK_REP = instance.get('ACK_REP', ACK_REP)
    PORT_PUB = instance.get('PORT_PUB', PORT_PUB)
    PORT_SUB = instance.get('PORT_SUB', PORT_SUB)
    PORT_WS = instance.get('PORT_WS', PORT_WS)
    HOSTNAME = instance.get('HOSTNAME', HOSTNAME)
    LOG_PATH = instance.get('LOG_PATH', LOG_PATH)
    DB_PATH = instance.get('DB_PATH', DB_PATH)
    DASHBOARD_PORT = instance.get('DASHBOARD_PORT', DASHBOARD_PORT)
    DASHBOARD_ENABLED = instance.get('DASHBOARD_ENABLED', DASHBOARD_ENABLED)
    PRIORITY_ENABLED = instance.get('PRIORITY_ENABLED', PRIORITY_ENABLED)
    MMAP_ENABLED = instance.get('MMAP_ENABLED', MMAP_ENABLED)
    MMAP_PATH = instance.get('MMAP_PATH', MMAP_PATH)
    MMAP_FILE = instance.get('MMAP_FILE', MMAP_FILE)


def fromYAML(yaml_file: str):
    global instance
    try:
        instance = YAMLConfig(yaml_file)
    except Exception as e:
        logger.error(e)
        instance = Config()
    instance.load_config()
    refresh()


def setValue(key: str, value: object, reload: bool = False):
    global instance
    instance.set(key, value)
    if reload:
        refresh()


def toYAML(yaml_file: str = YAML_FILE):
    global instance
    try:
        if isinstance(instance, YAMLConfig):
            instance.save()
    except Exception as e:
        logger.error(e)
