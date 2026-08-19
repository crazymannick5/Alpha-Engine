from pathlib import Path
from sqlalchemy import text
class HealthService:
    def __init__(self,engine,artifact_root): self.engine=engine; self.artifact_root=Path(artifact_root)
    def snapshot(self):
        db_ok=False
        try:
            with self.engine.connect() as c: db_ok=c.execute(text('select 1')).scalar_one()==1
        except Exception: pass
        return {'status':'READY' if db_ok and self.artifact_root.exists() else 'DEGRADED','database':db_ok,'artifact_store':self.artifact_root.exists()}
