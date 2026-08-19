import os, secrets
from fastapi import FastAPI,Header,HTTPException
from pydantic import BaseModel
from alpha_engine.storage.bootstrap import initialize
from alpha_engine.storage.models import CoreRecord, OperationRow
class QueryBody(BaseModel): record_type:str|None=None

def create_app(db_path='alpha.sqlite3', session_token:str|None=None):
    _,sf=initialize(db_path); token=session_token or secrets.token_urlsafe(32); app=FastAPI(title='Personal Alpha Engine Internal API',docs_url=None,redoc_url=None)
    def auth(x_alpha_session:str|None):
        if x_alpha_session!=token: raise HTTPException(401,'invalid local session')
    @app.get('/internal/v1/health')
    def health(x_alpha_session:str|None=Header(default=None)):
        auth(x_alpha_session); return {'status':'READY','api_version':'1','core_contract':'1.0'}
    @app.get('/internal/v1/records')
    def records(record_type:str|None=None,x_alpha_session:str|None=Header(default=None)):
        auth(x_alpha_session)
        with sf() as s:
            q=s.query(CoreRecord)
            if record_type:q=q.filter_by(record_type=record_type)
            return [{'id':r.id,'record_type':r.record_type,'kind':r.kind,'subject':r.subject,'payload_json':r.payload_json,'version':r.version} for r in q.limit(500).all()]
    @app.get('/internal/v1/operations')
    def operations(x_alpha_session:str|None=Header(default=None)):
        auth(x_alpha_session)
        with sf() as s:return [{'id':r.id,'type':r.op_type,'state':r.state} for r in s.query(OperationRow).limit(500).all()]
    app.state.session_token=token; return app

def main():
    import uvicorn
    token=secrets.token_urlsafe(32); print(f'ALPHA_SESSION={token}'); uvicorn.run(create_app(os.environ.get('ALPHA_DB','alpha.sqlite3'),token),host='127.0.0.1',port=int(os.environ.get('ALPHA_PORT','8765')))
