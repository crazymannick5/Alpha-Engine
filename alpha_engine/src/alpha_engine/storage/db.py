from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
class Base(DeclarativeBase): pass

def create_engine_sqlite(path: str|Path):
    eng=create_engine(f"sqlite:///{Path(path)}",future=True,connect_args={'check_same_thread':False,'timeout':5})
    @event.listens_for(eng,'connect')
    def configure(conn, _):
        c=conn.cursor(); c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA busy_timeout=5000'); c.close()
    return eng

def session_factory(engine): return sessionmaker(engine,expire_on_commit=False,future=True)
