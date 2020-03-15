from o3mq.config import fromYAML
fromYAML('./config/O3one.yaml')

from o3mq.backend import Backend

from o3mq.config import PORT_PUB, PORT_SUB
from o3mq import version_string

import time

from o3mq.plugins import Dashboard, WebSocketSub

version = version_string()
infos = f"Pub: {PORT_PUB} \t Sub: {PORT_SUB}"
header = f"""
\033[94m   oOO3 oo nn ee \033[39m
\033[94m oOO    OO NN EE \033[39m   {version}
\033[94m oOO    OO NN EE \033[39m   {infos}
\033[94m   oOO3 oo nn ee \033[39m   

"""

def init_console():
    import os
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

def enable_console_log():
    import sys
    import logging
    from o3mq.backend import logger

    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.INFO)
    logger.addHandler(consoleHandler)


if __name__ == "__main__":
    init_console()
    import sys
    sys.stdout.write(header)
    time.sleep(1)
    enable_console_log()

    # server = Backend({
        # 'persist_enabled': True,
        # 'mmap_enabled': False,
        # 'priority_enabled': False,
        # 'dashboard_enabled': True
    # })
    server = Backend()
    print("> O3one is ready!")

    server.inject_module(Dashboard())
    server.inject_module(WebSocketSub())

    # setValue('DASHBOARD_PORT', 9002)
    # toYAML()

    server.start()
