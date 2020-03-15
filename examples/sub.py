from common import *

from o3mq.config import PORT_PUB
from o3mq.backend import zmq
from o3mq.pubsub import SubSocketType



class Client:
    def __init__(self, port: str):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(SubSocketType.SUB.value)
        self.socket.connect("tcp://localhost:%s" % port)
        self.count = 0

    def __del__(self):
        self.socket.close()

    @staticmethod
    def output(publication: str):
        print(publication)

    def check(self):
        publication = self.socket.recv_string()
        self.count += 1
        if "o3 stop" == publication:
            print(self.count)
        self.output(publication)

    def subscribe(self, topic_name: str):
        self.socket.setsockopt_string(SubSocketType.SUBSCRIBE.value, topic_name)


if __name__ == "__main__":
    client = Client(PORT_PUB)
    client.subscribe('o3')
    print(f"Waiting for publications @ {PORT_PUB}")
    while True:
        client.check()

