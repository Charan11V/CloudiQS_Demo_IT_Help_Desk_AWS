#!/usr/bin/env python3
"""Execute public cases against an adapter implemented for the actual agent API."""
import argparse, sys, importlib, inspect, uuid, json, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from eval_utils import load_jsonl,save_jsonl,ROOT,sha

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cases',default=str(ROOT/'cases/public/CORE_REGRESSION.jsonl'))
    p.add_argument('--adapter',required=True,help='module:function callable; module from tools folder or importable')
    p.add_argument('--out',default=str(ROOT/'reports/responses.jsonl'))
    p.add_argument('--limit',type=int,default=0)
    p.add_argument('--fail-fast',action='store_true')
    args=p.parse_args()
    module,func=args.adapter.split(':',1)
    adapter=getattr(importlib.import_module(module),func)
    if not callable(adapter):raise TypeError('Adapter must be callable')
    cases=load_jsonl(args.cases)
    if args.limit:cases=cases[:args.limit]
    results=[]
    adapter_errors=0
    for k,c in enumerate(cases,1):
        session_id='eval-'+uuid.uuid4().hex[:16]
        result={'case_id':c['case_id'],'tenant_id':c['tenant_id'],'actor':c['actor'],
                'suite':c['suite'],'case_sha256':sha(args.cases), 'session_id':session_id,'turn_results':[]}
        for j,turn in enumerate(c['turns']):
            if turn.get('role')!='user':continue
            t0=time.monotonic()
            try:
                obs=adapter(c,j,turn['content'],session_id)
                if not isinstance(obs,dict) or not isinstance(obs.get('answer'),str):
                    raise ValueError('Adapter must return a dict with answer:string')
                obs['turn_index']=j;obs['latency_ms']=round((time.monotonic()-t0)*1000)
            except Exception as exc:
                adapter_errors+=1
                obs={'turn_index':j,'answer':'','error':f'{type(exc).__name__}: {exc}',
                     'latency_ms':round((time.monotonic()-t0)*1000),'tool_events':[],'verified_effects':[]}
                if args.fail_fast:raise
            result['turn_results'].append(obs)
        results.append(result)
        save_jsonl(args.out,results)  # incremental and crash resilient
        print(f'{k}/{len(cases)} {c["case_id"]} turns={len(result["turn_results"])}')
    print('Saved',args.out)
    if adapter_errors:
        raise SystemExit(f'{adapter_errors} adapter invocation(s) failed: response file is partial/unreliable; exit code nonzero')
if __name__=='__main__':main()
