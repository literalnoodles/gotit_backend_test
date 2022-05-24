import peewee
from dotenv import load_dotenv
from contextvars import ContextVar
import os

load_dotenv()
_env = os.getenv

DB_NAME = _env('DB_NAME')
DB_USER = _env("DB_USER")
DB_PW = _env("DB_PW")
DB_HOST = _env("DB_HOST")
DB_PORT = int(_env("DB_PORT"))

db_state_default = {
    "closed": None,
    "conn": None,
    "ctx": None,
    "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())


class PeeweeConnectionState(peewee._ConnectionState):
    def __init__(self, **kwargs):
        super().__setattr__("_state", db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        return self._state.get()[name]


db = peewee.MySQLDatabase(
    DB_NAME,
    user=DB_USER,
    password=DB_PW,
    host=DB_HOST,
    port=DB_PORT
)

db._state = PeeweeConnectionState()
