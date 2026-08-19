import argparse, json
from alpha_engine.reference_loop.runner import run

def main():
    p=argparse.ArgumentParser(prog='alpha'); sub=p.add_subparsers(dest='cmd',required=True); r=sub.add_parser('reference-loop'); r.add_argument('--db',default='alpha-reference.sqlite3'); r.add_argument('--artifacts',default='alpha-reference-artifacts'); args=p.parse_args()
    if args.cmd=='reference-loop': print(json.dumps(run(args.db,args.artifacts),indent=2))
if __name__=='__main__': main()
