from common import *

from o3mq.config import PORT_WS

import asyncio
import websockets


async def hello():
    uri = "ws://localhost:%s" % PORT_WS
    async with websockets.connect(uri) as websocket:
        # text = input("Post :")

        # await websocket.send(text)
        # print(f"> {text}")

        while True:
            revc = await websocket.recv()
            print(f"< {revc}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    print("Waiting for incoming Websocket messages ...")
    loop.run_until_complete(hello())
    loop.run_until_complete()
    while True:
        try:
            loop.run_forever()
        except:
            pass