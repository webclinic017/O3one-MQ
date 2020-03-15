import mmap
import platform
from queue import Queue
from threading import Condition
from heapq import heappush, heappop

mq = Queue()


class MessageQueue(list):
    def __init__(self) -> None:
        super().__init__()
        self._size = 0
        self._cv = Condition()

    def put(self, message: object, priority: int = 4) -> None:
        with self._cv:
            # heappush(self, (-priority, self._size, message))
            self.append(message)
            self._size += 1
            self._cv.notify()

    def pull(self) -> object:
        with self._cv:
            while len(self) == 0:
                self._cv.wait()
            #ret = heappop(self)[-1]
            ret = self.pop(-1)
            self._size -= 1
            return ret

    def size(self) -> int:
        return self._size

    def empty(self):
        with self._cv:
            return self._size == 0


class PriorityMessageQueue(list):
    def __init__(self) -> None:
        super().__init__()
        self._size = 0
        self._cv = Condition()

    def put(self, message: object, priority: int = 4) -> None:
        with self._cv:
            heappush(self, (-priority, self._size, message))
            # self.append(message)
            self._size += 1
            self._cv.notify()

    def pull(self) -> object:
        with self._cv:
            while len(self) == 0:
                self._cv.wait()
            ret = heappop(self)[-1]
            # ret = self.pop(-1)
            self._size -= 1
            return ret

    def size(self) -> int:
        return self._size

    def empty(self):
        with self._cv:
            return self._size == 0
