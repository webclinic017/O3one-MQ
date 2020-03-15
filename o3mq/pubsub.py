"""

Publisher / Subscriber model classes

"""
from enum import Enum

import zmq
from peewee import Model, TextField, CharField, SmallIntegerField
from o3mq.storage import instance
import struct

ACK_STATES = {
    "PENDING": 0,
    "ACK": 1,
    "REJECTED": 2,
    "RELOAD": 3
}


class SubSocketType(Enum):
    SUB = zmq.SUB
    SUBSCRIBE = zmq.SUBSCRIBE
    PULL = zmq.PULL
    REQ = zmq.REQ
    PUB = zmq.PUB


class PublicationBuilder:
    @classmethod
    def from_rep(cls, reponse):
        blocks = reponse.split(' ')
        title, content = blocks[0], ' '.join(blocks[1:])
        return Publication(title=title, content=content, state=0)  #


class PriorityPublicationBuilder:
    @classmethod
    def from_rep(cls, reponse):
        blocks = reponse.split(' ')
        if len(blocks) == 2:
            title, content = blocks[0], ' '.join(blocks[1:])
            return PriorityPublication(title=title, content=content, state=0)  #
        elif len(blocks) >= 3:
            try:
                title, prio, content = blocks[0], int(blocks[1]), ' '.join(blocks[2:])
            except Exception:
                title, content = blocks[0], ' '.join(blocks[2:])
                prio = 4
            return PriorityPublication(title=title, content=content, priority=prio, state=0)  #
        elif len(blocks) == 1:
            return PriorityPublication(title=blocks, content='', state=0)  #
        else:
            return PriorityPublication(title='', content='', state=0)  #


class PriorityPublication(Model):
    title = CharField(max_length=256)
    content = TextField()
    priority = SmallIntegerField(default=4)
    state = SmallIntegerField(default=0)

    class Meta:
        database = instance.get_store()


class Publication(Model):
    title = CharField(max_length=256)
    content = TextField()
    state = SmallIntegerField(default=0)

    class Meta:
        database = instance.get_store()

    def tobytes(self) -> bytes:
        blob = bytes(self.title, 'utf-8')
        blob += b'\x00'
        blob += bytes(self.content, 'utf-8')
        blob += b'\x00'
        blob += self.state.to_bytes(1, 'big')
        blob += b'\n'
        return blob


class Message(object):
    _current_state = None

    def __init__(self, *args, **kwargs):
        pass

    def ack(self):
        pass

    def reject(self):
        pass

    def reload(self):
        pass


class SubscriberList:
    def __init__(self):
        self.subs = dict([])

    def add(self, subscriber) -> bool:
        if subscriber not in self.subs:
            self.subs[subscriber] = 0
            return True
        return False
