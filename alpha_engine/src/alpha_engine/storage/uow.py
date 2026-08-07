from contextlib import AbstractContextManager
from sqlalchemy.orm import Session
class UnitOfWork(AbstractContextManager):
    def __init__(self, factory): self.factory=factory; self.session:Session|None=None
    def __enter__(self): self.session=self.factory(); return self
    def commit(self): assert self.session is not None; self.session.commit()
    def rollback(self):
        if self.session: self.session.rollback()
    def __exit__(self,t,v,tb):
        if self.session:
            if t is not None: self.session.rollback()
            self.session.close()
