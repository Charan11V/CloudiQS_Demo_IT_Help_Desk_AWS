#!/usr/bin/env python3
import sys,json,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from eval_utils import ROOT,all_public,all_gold,load_jsonl,ORACLE,PUBLIC,sha
public=all_public(); oracle=all_gold();issues=[]
if set(public)!=set(oracle):issues.append(f'Missing pairs: public_only={set(public)-set(oracle)}, oracle_only={set(oracle)-set(public)}')
for cid,p in public.items():
 g=oracle.get(cid)
 if 'expected_outcome' in p or 'required_facts' in p:issues.append(f'{cid}: oracle content in public case')
 if p['suite']!='ui_e2e' and not p.get('turns'):issues.append(f'{cid}: no turns')
 if p['suite']=='legacy_exploratory' and g and g['weight']!=0:issues.append(f'{cid}: legacy mistakenly weighted')
 if p['suite']!='legacy_exploratory' and g and g['weight']==0:issues.append(f'{cid}: strict case has no weight')
 if p.get('tenant_id') not in ('northstar','beacon'):issues.append(f'{cid}: unknown tenant')
 if not isinstance(p['actor'],dict) or not p['actor'].get('role'):issues.append(f'{cid}: missing role')
 if g and len(set(g.get('required_facts',[]))) != len(g.get('required_facts',[])):issues.append(f'{cid}: duplicated fact')
if issues:
 print('\n'.join(issues[:70]));sys.exit(1)
print('PASS case/oracle pairs',len(public),'sha256',sha(PUBLIC))
print('By suite',dict(collections.Counter(x['suite'] for x in public.values())))
print('Core regression',len(load_jsonl(ROOT/'cases/public/CORE_REGRESSION.jsonl')))
print('Private oracle kept in separate folder; do NOT mount in agent/Next.js public tree.')
