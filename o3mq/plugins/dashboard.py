import asyncio
import logging
from datetime import datetime

from aiohttp import web
from os.path import realpath, dirname

import aiohttp_jinja2
import jinja2
from dateutil.relativedelta import relativedelta

from o3mq.config import DASHBOARD_PORT, HOSTNAME
from o3mq.plugins.base import BaseModule
from o3mq.storage import get_path_for
from o3mq import version_string, __homepage__

logger = logging.getLogger()
logger.setLevel(logging.WARN)

class Dashboard(BaseModule):
    def __init__(self):
        super().__init__()
        self.app = web.Application()
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/dump', self.dump)
        self.app.router.add_get('/api', self.api)
        self.app.router.add_get('/admin', self.admin)
        self.app.router.add_get('/{name}', self.handle)
        self.app.add_routes([web.static('/static', '/'.join([dirname(__file__), '/dash_files/static']))])

        self.port = DASHBOARD_PORT
        self.host = HOSTNAME

        self.records_count = 0
        self.version_text = version_string(True)

        self.backend_instance = None
        self._init_logger()
        self._init_local()
        self._init_instance()

    def _init_logger(self):
        _logger = logging.getLogger('aiohttp.access')
        _logger.setLevel(logging.WARN)

    def _init_local(self):
        self.health_text = ''
        self.replication_text = ''
        self.records_text = ''
        self.uptime_text = ''

    def _init_instance(self):
        from o3mq.backend import backend_instances
        if len(backend_instances) > 0:
            self.backend_instance = backend_instances[0]
            self.health_text = self.backend_instance.health.value
            self.replication_text = ''
            if self.backend_instance.persist_enabled:
                self.replication_text += "SQL "
            if self.backend_instance.memory_map:
                self.replication_text += "MMAP "
            if self.replication_text == '':
                self.replication_text = 'disabled'
            self.records_text = f"{self.backend_instance.records['memory']} / {self.backend_instance.records['persist']}"

            self.start_time = self.backend_instance.start_time

    def update_uptime(self):
        if self.start_time is not None:
            now = datetime.now()
            dlt = relativedelta(now, self.start_time)
            dt = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
            human_readable = lambda delta: ['%d %s' % (getattr(delta, d), getattr(delta, d) > 1 and d or d[:-1]) for d in dt if getattr(delta, d)]
            ht = human_readable(dlt)
            self.uptime_text = 'just started' if  len(ht) < 1 else ht[0]

    def update_values(self):
        if self.backend_instance is not None:
            self.records_text = f"{self.backend_instance.records['memory']} / {self.backend_instance.records['persist']}"
            self.start_time = self.backend_instance.start_time

    async def api(self, request):
        self.update_values()
        self.update_uptime()
        context = {
            'instance_text': self.version_text,
            'health_text': self.health_text,
            'replication_text': self.replication_text,
            'records_text': self.records_text,
            'uptime_text': self.uptime_text
        }
        return web.json_response(context, status=201)

    async def index(self, request):
        self.update_values()
        self.update_uptime()
        context = {
            'instance_text': self.version_text,
            'instance_url': __homepage__,
            'health_text': self.health_text,
            'replication_text': self.replication_text,
            'records_text': self.records_text,
            'uptime_text': self.uptime_text
        }
        response = aiohttp_jinja2.render_template('index.jinja2', request, context)
        response.headers['Content-Language'] = 'ru'
        return response
        # return web.FileResponse(get_path_for(dirname(__file__),'dash_files/index.html'))

    async def dump(self, request):
        context = {
            'instance_text': self.version_text,
            'instance_url': __homepage__
        }
        response = aiohttp_jinja2.render_template('queue.jinja2', request, context)
        response.headers['Content-Language'] = 'ru'
        return response
        # return web.FileResponse(get_path_for(dirname(__file__), 'dash_files/dump.html'))

    async def admin(self, request):
        context = {
            'instance_text': self.version_text,
            'instance_url': __homepage__
        }
        response = aiohttp_jinja2.render_template('admin.jinja2', request, context)
        response.headers['Content-Language'] = 'ru'
        return response
        # return web.FileResponse(get_path_for(dirname(__file__), 'dash_files/dump.html'))


    async def handle(self, request):
        name = request.match_info.get('name', "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    def start(self, ioloop):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            print(e)
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()

        handler = web.AppRunner(self.app)
        aiohttp_jinja2.setup(self.app,
                             loader=jinja2.FileSystemLoader(get_path_for(dirname(__file__), 'dash_files/templates/')))
        loop.run_until_complete(handler.setup())
        coro = loop.create_server(handler.server, self.host, self.port)
        # asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def get_init_message(self) -> str:
        return f"Dashboard created ! Running at http://{self.host}:{self.port}/"