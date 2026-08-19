from dataclasses import dataclass
from pathlib import Path
@dataclass(frozen=True,slots=True)
class ProfilePaths:
    root:Path; db:Path; artifacts:Path; cache:Path; exports:Path; backups:Path; logs:Path; runtime:Path

def ensure_profile(root:str|Path)->ProfilePaths:
    r=Path(root); paths=ProfilePaths(r,r/'data'/'engine.sqlite3',r/'artifacts',r/'cache',r/'exports',r/'backups',r/'logs',r/'runtime')
    paths.db.parent.mkdir(parents=True,exist_ok=True)
    for p in [paths.artifacts,paths.cache,paths.exports,paths.backups,paths.logs,paths.runtime]: p.mkdir(parents=True,exist_ok=True)
    return paths
