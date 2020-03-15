import logging
import mmap
import os
import peewee
from peewee import SqliteDatabase
from o3mq.config import DB_PATH, MMAP_PATH, MMAP_FILE, MMAP_ENABLED

logger = logging.getLogger()

def get_path_for(base: str, name: str) -> str:
    return '/'.join([base, name])


class LocalStore:
    def __init__(self):
        self._locate_db()

    def _locate_db(self) -> None:
        if os.environ.get('SQL_DIALECT') == 'POSTGRESQL':
            # TODO: Postgresql support
            self.db = SqliteDatabase(get_path_for(DB_PATH, 'o3mq.db'))
        else:
            self.db = SqliteDatabase(get_path_for(DB_PATH, 'o3mq.db'))

    def get_store(self) -> object:
        return self.db


class MappedStorage:
    def __init__(self, path: str = MMAP_PATH, name: str = MMAP_FILE):
        self.path = path
        self.name = name
        self.enabled = MMAP_ENABLED
        self.fd = None
        self.mmap = None
        self._init_files_folder()

    def _init_files_folder(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if not os.path.isdir(self.path):
            logger.error(f"Invalid persist path : {self.path}. MMAP will be backed on RAM as fallback.")
            fname = -1
        else:
            fname = get_path_for(self.path, self.name)
        if os.path.exists(fname):
            self.fd = os.open(fname, os.O_RDWR)
            # TODO: reload from memory
        else:
            self.fd = os.open(fname, os.O_CREAT | os.O_TRUNC | os.O_RDWR)

    def create_map(self, size: int = 65532, name: str = "O3MQ"):
        self.mmap = mmap.mmap(self.fd, size, name, access=mmap.ACCESS_WRITE)


instance = LocalStore()
