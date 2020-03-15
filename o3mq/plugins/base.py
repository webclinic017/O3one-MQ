class BaseModule:

    def __init__(self):
        pass

    def start(self, ioloop):
        return

    def get_init_message(self) -> str:
        return f"{self.__class__.__name__} created !"