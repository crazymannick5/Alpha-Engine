from .db import Base, create_engine_sqlite, session_factory
from . import models

def initialize(path):
    engine=create_engine_sqlite(path); Base.metadata.create_all(engine); return engine, session_factory(engine)
