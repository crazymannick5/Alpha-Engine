from pathlib import Path
import hashlib, os, tempfile
from alpha_engine.kernel.ids import ArtifactId
from alpha_engine.storage.models import ArtifactRow
class ArtifactStore:
    def __init__(self, root: str|Path, session_factory): self.root=Path(root); self.sf=session_factory; self.root.mkdir(parents=True,exist_ok=True)
    def adopt_bytes(self,data:bytes,media_type='application/octet-stream'):
        digest=hashlib.sha256(data).hexdigest(); dest=self.root/'sha256'/digest[:2]/digest[2:4]/f'{digest}.blob'; dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            fd,tmp=tempfile.mkstemp(dir=dest.parent); os.close(fd); Path(tmp).write_bytes(data); os.replace(tmp,dest)
        with self.sf() as s:
            existing=s.query(ArtifactRow).filter_by(sha256=digest).one_or_none()
            if existing: return existing.id
            aid=str(ArtifactId.new()); s.add(ArtifactRow(id=aid,sha256=digest,size=len(data),media_type=media_type,path=str(dest))); s.commit(); return aid
    def verify(self,artifact_id:str)->bool:
        with self.sf() as s:
            row=s.get(ArtifactRow,artifact_id); data=Path(row.path).read_bytes() if row else b''
            return bool(row) and len(data)==row.size and hashlib.sha256(data).hexdigest()==row.sha256
