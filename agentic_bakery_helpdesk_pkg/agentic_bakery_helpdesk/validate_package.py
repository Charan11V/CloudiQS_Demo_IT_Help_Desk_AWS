#!/usr/bin/env python3
"""Validate the synthetic demo design package; run with python validate_package.py."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
seed=json.loads((P/'demo_seed.json').read_text())
cat=json.loads((P/'guided_flow_catalog.json').read_text())
cases=json.loads((P/'evaluation_cases.json').read_text())
assert seed['demo_mode'] is True
assert len(seed['tenants'])==2
assert len(seed['users'])==40
assert len(seed['devices'])==50
assert len(seed['tickets'])==80
assert len(seed['vpn_logs'])==150
assert len(seed['security_events'])==60
assert len(seed['knowledge_documents'])==25
assert len(cat['root_options'])==8
assert len(cat['issues'])==57
assert len(cases['cases'])==20
ids={x['issue_code'] for x in cat['issues']}
assert len(ids)==57
nested={leaf['id'] for group in cat['root_options'] for sub in group['children'] for leaf in sub['children']}
assert nested==ids,(nested^ids)
tenants={x['tenant_id'] for x in seed['tenants']}
users={(x['tenant_id'],x['user_id']):x for x in seed['users']}
devices={(x['tenant_id'],x['device_id']):x for x in seed['devices']}
apps={(x['tenant_id'],x['app_id']):x for x in seed['applications']}
for k in ['users','devices','tickets','accounts','sessions','vpn_profiles','mailboxes','applications','app_installations','entitlements','printers','print_jobs','services','security_events','vpn_logs','knowledge_documents','approval_requests','agent_runs','temporary_files','licence_pools','service_incidents','action_intents']:
 for row in seed[k]:
  assert row['tenant_id'] in tenants,(k,row)
for x in seed['devices']:
 assert (x['tenant_id'],x['assigned_to']) in users
 assert 0<=x['disk_free_gb']<=x['disk_total_gb']
 assert 0<=x['cpu_percent']<=100 and 0<=x['memory_percent']<=100
for x in seed['accounts']:
 assert (x['tenant_id'],x['user_id']) in users
for x in seed['vpn_profiles']:
 assert (x['tenant_id'],x['user_id']) in users
 assert (x['tenant_id'],x['device_id']) in devices
 assert devices[(x['tenant_id'],x['device_id'])]['assigned_to']==x['user_id']
for x in seed['app_installations']:
 assert (x['tenant_id'],x['user_id']) in users
 assert (x['tenant_id'],x['device_id']) in devices
 assert (x['tenant_id'],x['app_id']) in apps
 assert devices[(x['tenant_id'],x['device_id'])]['assigned_to']==x['user_id']
for x in seed['mailboxes']:
 assert (x['tenant_id'],x['user_id']) in users
 assert 0<=x['used_gb']<=x['quota_gb']
for x in seed['print_jobs']:
 assert (x['tenant_id'],x['user_id']) in users
 assert any(p['tenant_id']==x['tenant_id'] and p['printer_id']==x['printer_id'] for p in seed['printers'])
for x in seed['tickets']:
 assert (x['tenant_id'],x['requester_id']) in users
 assert x['issue_code'] in ids
for x in seed['temporary_files']:
 assert (x['tenant_id'],x['device_id']) in devices
 assert x['size_gb']>0 and x['category']=='temporary'
intents={x['action_id']:x for x in seed['action_intents']}
for a in seed['approval_requests']:
 assert a['action_intent_id'] in intents
 assert intents[a['action_intent_id']]['tenant_id']==a['tenant_id']
for incident in seed['service_incidents']:
 assert any(s['tenant_id']==incident['tenant_id'] and s['service_id']==incident['service_id'] for s in seed['services'])
for c in cases['cases']:
 assert (('northstar','NS-001') in users and ('beacon','BC-001') in users)
 assert any(x['user_id']==c['user_id'] for x in seed['users'])
 assert c['issue_code'] in ids or c['issue_code'].startswith('GEN-') or c['issue_code']=='MULTI'
assert next(x for x in seed['accounts'] if x['user_id']=='NS-001')['status']=='locked'
assert next(x for x in seed['devices'] if x['device_id']=='DEV-NS-001')['disk_free_gb']==12
assert sum(x['size_gb'] for x in seed['temporary_files'] if x['device_id']=='DEV-NS-001')==15
assert next(x for x in seed['services'] if x['service_id']=='beacon-vpn')['status']=='degraded'
assert next(x for x in seed['vpn_profiles'] if x['vpn_id']=='VPN-BC-001')['client_version']=='4.9'
print('PASS: 57 navigable issues / 8 categories / 40 users / 50 devices / 80 tickets / 20 evaluator cases; all checked relations consistent.')
