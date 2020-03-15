import logging
from threading import Thread

from o3mq.config import refresh
refresh()

from o3mq.config import PORT_WS, PORT_PUB
from o3mq.backend import zmq
import zmq.asyncio

from o3mq.plugins.base import BaseModule

import asyncio
import websockets

from o3mq.pubsub import SubSocketType

socket = None

logger = logging.getLogger()

def _init_logger():
    _logger = logging.getLogger('websockets.protocol')
    _logger.setLevel(logging.INFO)
    _logger = logging.getLogger('websockets.server')
    _logger.setLevel(logging.INFO)


def main():
    global socket
    ctx = zmq.Context()
    socket = ctx.socket(SubSocketType.SUB.value)
    socket.connect("tcp://localhost:%s" % PORT_PUB)
    socket.setsockopt_string(SubSocketType.SUBSCRIBE.value, 'o3')
    _init_logger()
    srv = WebSocketSubWorker()
    srv.start()
    print('Created !')
    start_server = websockets.serve(srv.handler, "localhost", PORT_WS)
    print('Starting ...')

    try:
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except Exception as e:
        logger.error(f"Cannot start Websocket : {e}")


async def server(ws, path):
    while True:
        publication = socket.recv_string()
        await ws.send(publication)


class WebSocketSubWorker(Thread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.connected = set()
        self.loop = asyncio.get_event_loop()

    def run(self) -> None:
        while self.running:
            publication = socket.recv_string()
            self.sendAll(publication)

    async def handler(self, ws, path):
        self.connected.add(ws)
        try:
            await ws.recv()
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected.remove(ws)

    def sendAll(self, pub):
        # TODO: thread safe self.connected
        for ws in self.connected:
            coro = ws.send(pub)
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)


class WebSocketSub(BaseModule):

    def start(self, ioloop):
        from multiprocessing import Process
        p = Process(target=main)
        p.start()


class WebSocketSubKO(BaseModule):

    def __init__(self):
        super().__init__()
        self.ws_server = ''
        self.port = 8765
        self.host = "localhost"

        self.ctx = zmq.asyncio.Context()
        self.socket = self.ctx.socket(SubSocketType.SUB.value)
        self.count = 0

        self.running = True

    def __del__(self):
        self.socket.close()

    def subscribe(self, topic: str = 'o3') -> None:
        self.socket.setsockopt_string(SubSocketType.SUBSCRIBE.value, topic)

    def connect(self):
        self.socket.connect("tcp://localhost:%s" % PORT_PUB)

    async def server(self, ws, path):
        msg = await self.socket.recv_multipart()

        # publication = self.socket.recv_string()
        self.count += 1
        await ws.send(msg)
        print(f"> {msg}")
        # name = await ws.recv()
        # greeting = f"Hello {name}!"
        # await ws.send(greeting)
        # print(f"> {greeting}")

    def start_server(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            print(e)
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()

        handler = websockets.serve(self.server, self.host, self.port, loop=loop)
        # asyncio.set_event_loop(loop)
        loop.run_until_complete(handler)
        loop.run_forever()

    def handle(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        handler = websockets.serve(self.server, self.host, self.port)
        print("starting ws")
        asyncio.get_event_loop().run_until_complete(handler)
        asyncio.get_event_loop().run_forever()

    def start(self, ioloop):

        self.subscribe()
        self.connect()
        t = Thread(target=self.handle)
        t.start()


        #
        # try:
        #     loop = asyncio.get_event_loop()
        # except RuntimeError as e:
        #     print(e)
        #     asyncio.set_event_loop(asyncio.new_event_loop())
        #     loop = asyncio.get_event_loop()
        #
        # handler = websockets.serve(self.server, self.host, self.port, loop=loop)
        # # asyncio.set_event_loop(loop)
        # loop.run_until_complete(handler)
        # loop.run_forever()



    def get_init_message(self) -> str:
        return f"WebSocket subscriber bridge created ! Running at ws://{self.host}:{self.port}"
