"""HELIO eval utility module. Stdlib only."""
from __future__ import annotations
from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'cases/public/ALL_CASES.jsonl'
ORACLE=ROOT/'cases/private_oracle/ALL_ORACLE_DO_NOT_EXPOSE_TO_AGENT.jsonl'
def load_jsonl(path):
    rows=[]
    for i,line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(),1):
        if line.strip():
            try: rows.append(json.loads(line))
            except Exception as exc: raise ValueError(f'{path}:{i}: {exc}') from exc
    return rows
def save_jsonl(path,rows):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def all_public():return {r['case_id']:r for r in load_jsonl(PUBLIC)}
def all_gold():return {r['case_id']:r for r in load_jsonl(ORACLE)}
def valid_responses(rows):
    issues=[];seen=set()
    for i,r in enumerate(rows,1):
        id=r.get('case_id')
        if not id:issues.append(f'row {i}: missing case_id')
        if id in seen:issues.append(f'row {i}: duplicate {id}')
        seen.add(id)
        if not isinstance(r.get('turn_results'),list):
            issues.append(f'row {i}: turn_results must be list')
            continue
        for j,t in enumerate(r.get('turn_results',[]),1):
            if not isinstance(t,dict):
                issues.append(f'{id} turn {j}: expected object')
                continue
            if not isinstance(t.get('answer',''),str):issues.append(f'{id} turn {j}: answer must be string')
            if 'tool_events' in t and not isinstance(t['tool_events'],list):issues.append(f'{id} turn {j}: tool_events must be list')
            if 'verified_effects' in t and not isinstance(t['verified_effects'],list):issues.append(f'{id} turn {j}: verified_effects must be list')
    return issues
