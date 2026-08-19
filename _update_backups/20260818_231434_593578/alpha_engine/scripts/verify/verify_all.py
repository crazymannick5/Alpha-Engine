import subprocess,sys
steps=[[sys.executable,'-m','pytest','-q'],[sys.executable,'-m','alpha_engine.reference_loop.runner','--db','verify-reference.sqlite3','--artifacts','verify-artifacts']]
failed=0
for cmd in steps:
    print('RUN',cmd); r=subprocess.run(cmd,text=True); print('EXIT',r.returncode); failed += (r.returncode!=0)
raise SystemExit(1 if failed else 0)
