import logging
import os
import struct
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from mmap import mmap
from threading import Condition, Thread

import zmq
import asyncio
import zmq.asyncio
import base64
import sys

from aiohttp.web import Application

from peewee import OperationalError

from o3mq.config import refresh

refresh()

from o3mq.mqueue import MessageQueue, PriorityMessageQueue
from o3mq.pubsub import Publication, ACK_STATES, PublicationBuilder, PriorityPublication, PriorityPublicationBuilder
from o3mq.storage import LocalStore, get_path_for, MappedStorage
from o3mq.topic import Topic
from o3mq.config import DEFAULT_CONNECT_TIMEOUT, PERSIST_ENABLED, ACK_REP, PORT_PUB, PORT_SUB, HOSTNAME, LOG_PATH, \
    DB_PATH, PRIORITY_ENABLED, DASHBOARD_ENABLED, MMAP_ENABLED
from o3mq.plugins.base import BaseModule

logger = logging.getLogger()
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)
logging.basicConfig(filename=get_path_for(LOG_PATH, 'o3-debug.log'), level=logging.INFO)


class SocketType(Enum):
    PUB = zmq.PUB
    REP = zmq.REP


class HealthTypes(Enum):
    OK = "good"
    OVERLOADED = "overloaded"
    OVERFLOWED = "overflowed"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class Connection(zmq.asyncio.Context):
    hostname = None
    port = None
    connect_timeout = DEFAULT_CONNECT_TIMEOUT
    _closed = True
    _connection = None
    password = None

    def __init__(self, hostname: str = HOSTNAME, ports: list = [PORT_PUB, PORT_SUB], password=None, **kwargs):
        super().__init__()
        self.hostname = hostname
        self.port = ports
        self.password = base64.b64encode(f'o3-{password}'.encode('utf-8'))  # sorry
        self.connect_timeout = kwargs.get("timeout", self.connect_timeout)
        self._closed = None

    def _establish_connection(self):
        self._connection = zmq.asyncio.Context()
        logger.debug("connected to zmq")

    def _terminate_connection(self):
        self._connection.destroy()
        logger.debug("destroying connection to zmq")

    def connect(self):
        self._establish_connection()
        self._closed = False

    def close(self):
        self._terminate_connection()
        self._closed = True

    @property
    def open(self):
        return not self._closed

    @property
    def connection(self):
        if self._closed:
            return
        if not self._connection:
            self._establish_connection()
            self._closed = False
        return self._connection

    def get_pub_port(self) -> int:
        return self.port[0] if len(self.port) > 0 else PORT_PUB

    def get_sub_port(self) -> int:
        return self.port[1] if len(self.port) > 1 else PORT_SUB

    def get_pub_url(self) -> str:
        return f"tcp://{self.hostname}:{self.get_pub_port()}"

    def get_sub_url(self):
        return f"tcp://{self.hostname}:{self.get_sub_port()}"


backend_instances = []


class ArgsParser:
    @classmethod
    def parseBoolean(cls, conf: dict, arg: str, default: bool) -> bool:
        if arg in conf:
            if conf[arg] is True:
                logger.info(f"{arg.title()} True (from launch arguments).")
                return True
            else:
                logger.info(f"{arg.title()} False (from launch arguments).")
                return False
        return default


class Backend(object):
    default_port = None
    extras = None
    memory_map = None
    persist_enabled = PERSIST_ENABLED
    mmap_enabled = MMAP_ENABLED
    priority_enabled = PRIORITY_ENABLED
    dashboard_enabled = DASHBOARD_ENABLED

    def __init__(self, config: dict = {}, **kwargs):
        self.modules = []
        self.conf = config
        self.extras = kwargs.get("extras")
        self._cv = Condition()
        self.queue = MessageQueue()
        self.running = False
        self.health = HealthTypes.OK

        self.mmap_header_size = 3
        self.max_load = 65535 - self.mmap_header_size
        self.max_records = 2 ** ((self.mmap_header_size << self.mmap_header_size) - 1) - 1
        self.mmap_last_pos = 0
        self.reloaded = False
        self.mmap_rewrite = False

        self.records = {
            'persist': 0,
            'memory': 0
        }

        self._cv = Condition()

        self._pre_init()

        self._init_config()
        self._create_structs()
        self._init_sockets()

        self._post_init()

    def _init_config(self):
        self.persist_enabled = ArgsParser.parseBoolean(self.conf, arg='persist_enabled', default=self.persist_enabled)
        self.dashboard_enabled = ArgsParser.parseBoolean(self.conf, arg='dashboard_enabled',
                                                         default=self.dashboard_enabled)
        self.mmap_enabled = ArgsParser.parseBoolean(self.conf, arg='mmap_enabled', default=self.mmap_enabled)
        self.priority_enabled = ArgsParser.parseBoolean(self.conf, arg='priority_enabled',
                                                        default=self.priority_enabled)

        logger.info("Loaded config from parameters.")

    def _create_structs(self):
        if self.persist_enabled:
            self.persist_queue = MessageQueue()
            self.topics = {}
            try:
                if self.priority_enabled:
                    PriorityPublication.create_table()  # Try to create publication table in db
                else:
                    Publication.create_table()  # Try to create publication table in db
                Topic.create_table()  # Try to create topics table in db
            except OperationalError as e:
                logger.error("Unable to create persistent database. Got : ", e)

        if self.mmap_enabled:
            self.mapped = MappedStorage()
            # self.memory_map = mmap(-1, self.max_load, "O3MQ")
            self.mapped.create_map(self.max_load, "O3MQ")
            self.memory_map = self.mapped.mmap
            self.reload_map()
            self.mmap_rewrite = False

    def _init_sockets(self):
        self.ctx = Connection()

        self.pubsub_socket = self.ctx.socket(SocketType.PUB.value)
        try:
            logger.info(f"Creating Pub server with uri: {self.ctx.get_pub_url()}")
            self.pubsub_socket.bind(self.ctx.get_pub_url())
        except Exception as e:
            logger.critical(
                "Cannot create publishing server. The server will now stop. Please refer to the following error for more details :")
            logger.error(e)
            sys.exit(1)
        self.server_socket = self.ctx.socket(SocketType.REP.value)
        try:
            logger.info(f"Creating Sub server with uri: {self.ctx.get_sub_url()}")
            self.server_socket.bind(self.ctx.get_sub_url())
        except Exception as e:
            logger.critical(
                "Cannot create subscribing server. The server will now stop. Please refer to the following error for more details :")
            logger.error(e)
            sys.exit(1)

        logger.info(f"Connexion established -- client {self.ctx.get_sub_url()}, pubsub {self.ctx.get_pub_url()}")

        self.running = True

    def _post_init(self):
        global backend_instances
        backend_instances.append(self)

    def __del__(self):
        try:
            self.server_socket.close()
        except AttributeError:
            pass

        try:
            self.pubsub_socket.close()
        except AttributeError:
            pass

        self.running = False

    def reload_map(self):
        if not self.mmap_enabled:
            return
        self.memory_map.seek(0)
        headers = self.memory_map[:3]
        void_mark = not (headers[0] >= 128)
        if void_mark:
            return
        found_pos, = struct.unpack('>I', b'\x00' + headers)
        found_pos -= 2 << 22  # remove void-mark to parse
        if found_pos <= self.max_load:
            self.mmap_last_pos = found_pos
            self.reloaded = True

    @staticmethod
    def on_pub(instance, publication: Publication) -> None:
        publication.state = 1  # ACK_STATES['ACK']
        # if instance.persist:
        #     publication.save()
        # logger.info(f"Publication saved : {publication.content}")

    def ensure_topic(self, topic_name: str):
        if self.persist_enabled:
            if topic_name not in self.topics:
                topic: Topic = Topic(name=topic_name)
                # topic.save()
                self.topics[topic_name] = topic

    def init_mmap(self):
        """
        3 first bytes are used to update clients & tell mmap size
        """
        if self.reloaded:
            return
        if self.queue.empty():
            self.empty_map()
        else:
            self.memory_map.seek(0)
            self.memory_map[0] = self.memory_map[0] % 128  # Void-mark first byte

    def finish_mmap(self):
        self.memory_map.seek(0)
        lp = self.mmap_last_pos
        if lp > self.max_records:
            lp = self.max_records
            self.health = HealthTypes.OVERFLOWED
        elif lp > self.max_load:
            lp = lp % self.max_load
            self.health = HealthTypes.OVERLOADED
        elif lp > (self.max_records >> 4):
            self.health = HealthTypes.DEGRADED
        lp += (self.max_records + 1)  # Un Void-mark first byte
        self.memory_map.write(lp.to_bytes(3, 'big'))

    def store_mmap(self, pub: Publication) -> None:
        self.memory_map.seek(self.mmap_last_pos + self.mmap_header_size)

        pub_byte = pub.tobytes()
        lb = len(pub_byte)
        if (lb + self.mmap_last_pos + self.mmap_header_size) >= self.max_load:
            sep = self.max_load - (self.mmap_last_pos + self.mmap_header_size)
            self.memory_map.write(pub_byte[:sep])
            self.memory_map.seek(self.mmap_header_size)
            self.memory_map.write(pub_byte[sep:])
            self.mmap_last_pos = lb - sep
            self.mmap_rewrite = True
        else:
            self.memory_map.write(pub_byte)  # TODO: if overflow, write [:limit], seek(0+3), write [limit:]
            self.mmap_last_pos += lb % self.max_load
            if not self.persist_enabled and not self.mmap_rewrite:
                self.records['persist'] += 1

        # qsz = self.queue.size()
        # if qsz > self.max_records:
        #     sz = self.max_records
        #     self.health = HealthTypes.OVERFLOWED
        # elif qsz > self.max_load:
        #     sz = qsz
        #     self.health = HealthTypes.OVERLOADED
        # elif qsz > (self.max_load >> 1):
        #     self.health = HealthTypes.DEGRADED
        #     sz = qsz
        # else:
        #     sz = qsz
        #     if self.health != HealthTypes.OK:
        #         self.health = HealthTypes.OK
        # sz = min(self.queue.size(), 8388607)
        # sz.to_bytes(self.mmap_header_size, 'big')
        # self.memory_map.write(sz)  # write size with void-mark

        # self.memory_map.seek(self.mmap_last_pos)

        # Write all here

        # self.memory_map.seek(0)

    def empty_map(self, flush: bool = True) -> None:
        """
        If the map first byte starts with b'0', then the map is void-marked.
        Void-mark indicate that the map have been stopped in a task and is corrupted.
        If the file start with x0..{23} then the queue is empty (and the file didn't need
        to be read). The 1-24 bytes are used as "first byte position" in map.
        :param flush: indicate if the map is flushed after void-mark
        """
        self.memory_map.seek(0)
        self.memory_map.write(b'\x00\x00\x00')
        self.mmap_last_pos = 0
        if flush:
            self.memory_map.flush()

    async def post(self, publication: Publication) -> None:
        await self.pubsub_socket.send_string("%s %s" % (publication.title, publication.content), )
        # print("Publication %s sended..." % publication.content)
        self.on_pub(self, publication)

    async def reply(self):
        if self.mmap_enabled:
            self.init_mmap()
        content = 0
        while self.running:

            if not self.queue.empty() and self.mmap_enabled:
                self.init_mmap()
            while not self.queue.empty():
                content = 1
                pub: Publication = self.queue.pull()
                await self.post(pub)
                if self.mmap_enabled:
                    self.store_mmap(pub)
                if self.persist_enabled:
                    self.persist_queue.put(pub)
            if self.mmap_enabled and content != 0:
                self.finish_mmap()
                content = False
            await asyncio.sleep(0)

    async def persistence(self):
        while self.persist_enabled:
            while not self.persist_queue.empty():
                pub: Publication = self.persist_queue.pull()
                self.records['persist'] += 1
                pub.save()
                self.ensure_topic(pub.title)

            await asyncio.sleep(0)

    async def wait(self):
        while True:
            rep = await self.server_socket.recv_string()
            await self.server_socket.send_string(ACK_REP)
            self.records['memory'] += 1

            if not self.priority_enabled:
                publication = PublicationBuilder.from_rep(rep)
                self.queue.put(publication)
            else:
                publication = PriorityPublicationBuilder.from_rep(rep)
                self.queue.put(message=publication, priority=publication.priority)

    @staticmethod
    def persist_pub(publication: Publication):
        try:
            publication.save()
            # logger.info(f"Publication saved : {publication.content}")
        except OperationalError as e:
            logger.error("Persistence failed.")

    def start(self):
        ioloop = asyncio.get_event_loop()
        ioloop.create_task(self.wait())
        ioloop.create_task(self.reply())
        if self.persist_enabled:
            ioloop.create_task(self.persistence())

        for mod in self.modules:
            mod_start = getattr(mod, "start", None)
            mod_start_init_msg = getattr(mod, "get_init_message", None)
            if callable(mod_start):
                try:
                    mod_start(ioloop)
                    ioloop = asyncio.get_event_loop()
                    logger.info(f"Loading module {mod.__class__.__name__}")
                    if callable(mod_start_init_msg):
                        logger.info(mod_start_init_msg())
                except Exception as e:
                    logger.error(e)

            # coro = ioloop.create_server(app.make_handler(), "localhost", 9000)
            # server = ioloop.run_until_complete(coro)
        ioloop.run_forever()

    def q_delete(self):
        pass

    def q_declare(self):
        pass

    def q_bind(self):
        pass

    def _pre_init(self):
        self.start_time = datetime.now()
        logger.info("oO0 = O3one is starting = 0Oo ")

    def inject_module(self, module: BaseModule):
        self.modules.append(module)


if __name__ == "__main__":
    server = Backend({
        'persist_enabled': True,
        'memory_map': True,
        'priority_enabled': True
    })
    # server = Server(5555)
    server.start()
