"""Aggregate role/tenant variants; semantic correctness requires gold-aware judging.
This tool highlights whether an entire group was verified, and which actors failed.
"""
import sys,json,argparse,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from eval_utils import all_gold,load_jsonl
p=argparse.ArgumentParser();p.add_argument('--grades',required=True);p.add_argument('--out',required=True);a=p.parse_args()
gold=all_gold(); groups=collections.defaultdict(list)
for row in load_jsonl(a.grades):
 if row.get('suite')!='metamorphic':continue
 g=gold[row['case_id']]; grp=g['acceptance_checks'].get('compare_group','unknown')
 groups[grp].append({'case_id':row['case_id'],'status':row['status'],'semantic_score':row['semantic_score'],'trace_check':row['trace_check']})
result={'groups':{k:{'variants':v,'any_failure':any(x['status'].startswith('FAIL') for x in v),'all_verified':all(x['status']=='PASS_VERIFIED' for x in v)} for k,v in groups.items()},'note':'This is an aggregation not independent proof of access control; check event traces and role-specific oracles.'}
Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
print('Metamorphic groups',len(groups),'Failures',sum(x['any_failure'] for x in result['groups'].values()))
