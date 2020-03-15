from peewee import Model, CharField, IntegerField

from o3mq.pubsub import SubscriberList
from o3mq.mqueue import MessageQueue
from o3mq.storage import instance


class Topic(Model):
    name = CharField(max_length=256)
    id = IntegerField()

    _id_counter: int = 0

    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Topic._id_counter += 1

        self.name = name
        self.id = Topic._id_counter
        self.messages = MessageQueue()
        self.subscribers = SubscriberList()

    def add_subscriber(self, subscriber):
        if self.subscribers.add(subscriber):
            self.send_messages()

    def add_message(self, message):
        self.messages.append(message)
        self.send_messages()

    def send_messages(self):
        for sub in self.subscribers:
            index = self.subscribers[sub]
            while self.messages.size() > index:
                msg = "SUB:" + self.name + ":" + self.messages.pull()
                sub.send_message(msg)
            self.subscribers[sub] = self.messages.size()

    def save(self, force_insert=False, only=None):
        self.id = Topic._id_counter
        Topic._id_counter += 1
        super().save(force_insert, only)

    class Meta:
        database = instance.get_store()
