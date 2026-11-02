#!/usr/bin/env python3
"""Deterministic dataset QA and linkage tests (not LLM evaluation)."""
import json,sqlite3,pathlib,hashlib,collections
root=pathlib.Path(__file__).resolve().parents[1]
D=root/'data'
read=lambda p:json.loads((root/p).read_text())
rows=lambda p:[json.loads(x) for x in (root/p).read_text().splitlines() if x.strip()]
manifest=read('data/manifest.json');sources=read('data/source_registry.json')
features=read('data/feature_inventory.json');tools=read('data/agent_tool_contracts.json')
scenarios=rows('data/evaluation/scenarios.jsonl');oracle=rows('data/evaluation/ground_truth_DO_NOT_EXPOSE_TO_AGENT.jsonl')
assert len(sources)==47,(len(sources),'sources')
assert len(features)==114,(len(features),'features')
assert len(tools)==32
assert len(scenarios)==len(oracle)==160
assert len(set(s['case_id'] for s in scenarios))==160
assert {s['case_id'] for s in scenarios}=={o['case_id'] for o in oracle}
assert len(read('data/fixtures/conflict_manifest.json'))==20
assert len(read('data/fixtures/fault_catalog.json'))==12
assert manifest['real_personal_data']==False
assert all(t['domain'].endswith('.example') for t in read('data/tenants.json'))
with sqlite3.connect(D/'canonical'/'enterprise.sqlite') as c:
 c.row_factory=sqlite3.Row
 assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
 assert c.execute('select count(*) from users').fetchone()[0]==40
 assert c.execute('select count(*) from devices').fetchone()[0]==50
 assert c.execute('select count(*) from tickets').fetchone()[0]==80
 assert c.execute('select count(*) from knowledge_documents').fetchone()[0]==27
 assert c.execute('select count(*) from source_records').fetchone()[0]==manifest['counts']['knowledge_index']+sum(v for k,v in manifest['counts'].items() if k in {s['source_key'] for s in sources} and k!='knowledge_index')
 for row in c.execute('select * from tickets'):
  assert c.execute('select 1 from users where tenant_id=? and user_id=?',(row['tenant_id'],row['requester_id'])).fetchone(),(row['ticket_id'],'orphan requester')
 for row in c.execute('select * from devices'):
  assert c.execute('select 1 from users where tenant_id=? and user_id=?',(row['tenant_id'],row['owner_user_id'])).fetchone(),(row['device_id'],'orphan owner')
 for row in c.execute('select * from knowledge_documents'):
  doc=json.loads(row['metadata']);content=(root/doc['path']).read_text()
  assert hashlib.sha256(content.encode()).hexdigest()==doc['content_sha256'],doc['document_id']
 assert c.execute("select count(*) from tickets where tenant_id='northstar'").fetchone()[0]==60
 assert c.execute("select count(*) from tickets where tenant_id='beacon'").fetchone()[0]==20
 assert c.execute("select json_extract(json_record,'$.account_state') from source_records where source_key='identity_directory' and tenant_id='northstar' and json_extract(json_record,'$.employee_id')='northstar-EMP-0001'").fetchone()[0]=='locked'
 assert c.execute("select json_extract(json_record,'$.employment_status') from source_records where source_key='hris_people' and tenant_id='northstar' and json_extract(json_record,'$.person_key')='northstar-EMP-0009'").fetchone()[0]=='terminated'
# Independent source files contain only correct tenant, no stray PII domains.
records_total=0
for source in sources:
 count=0
 for tenant in ['northstar','beacon']:
  f=D/'raw'/source['source_key']/(tenant+'.jsonl')
  assert f.exists(),f
  for r in rows(f.relative_to(root)):
   assert r['tenant_id']==tenant,(source['source_key'],r.get('tenant_id'))
   count+=1
 assert count==source['records'],(source['source_key'],count,source['records'])
 records_total+=count
assert records_total==sum(s['records'] for s in sources)
report={'ok':True,'two_tenants':True,'source_feeds':len(sources),'source_records':records_total,'people':40,'devices':50,'tickets':80,'kb_documents':27,'documented_conflicts':20,'fault_catalogue':12,'feature_specifications':len(features),'candidate_tool_contracts':len(tools),'eval_cases_not_yet_run':len(scenarios),'warning':'Dataset integrity checks only. This is NOT an AI agent model evaluation and does not certify security.'}
(root/'docs'/'VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
