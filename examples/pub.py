from common import *

from o3mq.config import refresh
refresh()

from o3mq.config import PORT_PUB, PORT_SUB
from o3mq.backend import zmq
from o3mq.pubsub import SubSocketType

class Publisher:
    def __init__(self, port):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(SubSocketType.REQ.value)
        self.socket.connect("tcp://localhost:%s" % str(int(port)))

    def __del__(self):
        self.socket.close()

    def send_publication(self, publication: str):
        self.socket.send_string(publication)
        self.socket.recv_string()


def stress_test():
    publ = Publisher(PORT_SUB)
    input("Press any key to start test : ")
    for i in range(0, 5000):
        publ.send_publication("o3 spam")
    publ.send_publication("o3 stop")


if __name__ == "__main__":
    from sys import argv

    stress = "stress" in argv


    if stress:
        stress_test()
    else:
        name = "o3"
        publisher = Publisher(PORT_SUB)
        while True:
            publication = input("Publication: ")
            print("%s %s" % (name, publication))
            publisher.send_publication("%s %s" % (name, publication))
