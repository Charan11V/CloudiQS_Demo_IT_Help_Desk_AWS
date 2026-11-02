"""Northstar/Beacon enterprise IT data simulator. Synthetic only; NOT a production auth service.
Run: uvicorn mock_api.app:app --reload --port 8000 (from pack root).
API integrations are mocked. No Bedrock/AgentCore call is included.
"""
from __future__ import annotations
import os, json, sqlite3, hashlib, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field, ConfigDict
ROOT=Path(__file__).resolve().parents[1]
DB=Path(os.getenv('ENTERPRISE_DEMO_DB',str(ROOT/'data'/'runtime.sqlite')))
TOKENS=json.loads((ROOT/'data'/'fixtures'/'demo_tokens_INSECURE_PUBLIC.json').read_text())
app=FastAPI(title='Fictional Enterprise IT Integrations API',description='Synthetic HRIS/IdP/ITSM/MDM/VPN/KB gateway. DEV TOKENS ONLY. Never deploy publicly.',version='1.0.0')
def utcnow():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def parse_date(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def dumps(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def stable_hash(x):return hashlib.sha256(dumps(x).encode()).hexdigest()
@contextmanager
def dbc():
 c=sqlite3.connect(DB,timeout=20,isolation_level=None)
 c.row_factory=sqlite3.Row
 c.execute('PRAGMA busy_timeout=20000')
 # Create tables if not exists
 c.execute('''CREATE TABLE IF NOT EXISTS ticket_comments(
  tenant_id TEXT NOT NULL,
  comment_id TEXT NOT NULL,
  ticket_id TEXT NOT NULL,
  author_id TEXT NOT NULL,
  body TEXT NOT NULL,
  visibility TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(tenant_id,comment_id))''')
 c.execute('''CREATE TABLE IF NOT EXISTS escalations(
  tenant_id TEXT NOT NULL,
  escalation_id TEXT NOT NULL,
  ticket_id TEXT,
  creator_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  evidence_ids TEXT,
  severity TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(tenant_id,escalation_id))''')
 try:yield c
 finally:c.close()
def actor(authorization:str|None=Header(default=None)):
 if not authorization or not authorization.lower().startswith('bearer '):raise HTTPException(401,'Use a fictional demo Bearer token from data/fixtures/demo_tokens_INSECURE_PUBLIC.json')
 demo_token=authorization.split(' ',1)[1].strip()
 uid=TOKENS.get(demo_token)
 if not uid:raise HTTPException(401,'Invalid demo token')
 with dbc() as c:
  row=c.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone()
 if not row or row['status']=='terminated':raise HTTPException(401,'Identity disabled or inactive; HR lifecycle may require reconciliation')
 return dict(row)
def staff(a):return a['role'] in ('it_engineer','it_manager','tenant_admin','security_analyst','hr_partner')
def can_manage_tickets(a):return a['role'] in ('it_engineer','it_manager','tenant_admin','security_analyst')
def assert_own_or_support(a,uid):
 if uid!=a['user_id'] and not staff(a):raise HTTPException(403,'Not authorised to inspect another user')
def audit(c,a,action,resource,outcome,detail=None):
 c.execute('INSERT INTO audit_log(tenant_id,actor_id,action,resource,result,at,detail) VALUES(?,?,?,?,?,?,?)',(a['tenant_id'],a['user_id'],action,resource,outcome,utcnow(),dumps(detail or {})))
def data_rows(c,source,tenant):
 return [json.loads(x['json_record']) for x in c.execute('SELECT json_record FROM source_records WHERE tenant_id=? AND source_key=?',(tenant,source))]
def one_source(c,source,tenant,key,val):
 return next((x for x in data_rows(c,source,tenant) if x.get(key)==val),None)
def visible_doc(role,classification):
 if classification=='employees':return True
 if classification=='internal':return role in ('it_engineer','it_manager','tenant_admin','security_analyst','hr_partner')
 if classification=='admin':return role=='tenant_admin'
 if classification=='security':return role=='security_analyst'
 return False

@app.get('/health')
def health():return {'ok':DB.exists(),'mode':'synthetic_mock_only','db':DB.name,'no_real_identity_provider':True}
@app.get('/v1/me')
def me(a=Depends(actor)):
 return {k:a[k] for k in ('tenant_id','user_id','name','email','role','department','status')}
@app.get('/v1/tenant')
def tenant(a=Depends(actor)):
 with dbc() as c:
  row=c.execute('SELECT metadata FROM tenants WHERE tenant_id=?',(a['tenant_id'],)).fetchone()
 return json.loads(row['metadata'])
@app.get('/v1/users')
def users(search:str='',limit:int=Query(25,ge=1,le=100),a=Depends(actor)):
 with dbc() as c:
  if not staff(a):rows=c.execute('SELECT user_id,name,email,department,role,status FROM users WHERE tenant_id=? AND user_id=?',(a['tenant_id'],a['user_id'])).fetchall()
  else:rows=c.execute('SELECT user_id,name,email,department,role,status FROM users WHERE tenant_id=? AND (lower(name) LIKE ? OR lower(email) LIKE ?) LIMIT ?', (a['tenant_id'],'%'+search.lower()+'%','%'+search.lower()+'%',limit)).fetchall()
 return [dict(r) for r in rows]
@app.get('/v1/identity/accounts/{user_id}')
def identity_account(user_id:str,a=Depends(actor)):
 assert_own_or_support(a,user_id)
 with dbc() as c:
  x=one_source(c,'identity_directory',a['tenant_id'],'employee_id',user_id)
 if not x:raise HTTPException(404,'Account not found in your tenant')
 return {k:x[k] for k in ('tenant_id','employee_id','displayName','accountEnabled','account_state','department','signInActivity','last_synced_at')}
@app.get('/v1/identity/signins/{user_id}')
def identity_signins(user_id:str,a=Depends(actor)):
 assert_own_or_support(a,user_id)
 with dbc() as c:
  records=[x for x in data_rows(c,'identity_signins',a['tenant_id']) if x['user_id']==user_id]
 return records[:25]
@app.get('/v1/devices')
def devices(user_id:str|None=None,a=Depends(actor)):
 if user_id and user_id!=a['user_id'] and not staff(a):raise HTTPException(403,'Not authorised')
 with dbc() as c:
  if not staff(a):rows=c.execute('SELECT * FROM devices WHERE tenant_id=? AND owner_user_id=?',(a['tenant_id'],a['user_id'])).fetchall()
  elif user_id:rows=c.execute('SELECT * FROM devices WHERE tenant_id=? AND owner_user_id=?',(a['tenant_id'],user_id)).fetchall()
  else:rows=c.execute('SELECT * FROM devices WHERE tenant_id=? LIMIT 100',(a['tenant_id'],)).fetchall()
  out=[]
  for r in rows:
   item=json.loads(r['attributes'])
   # Prefer hostname as display name when UI looks for device_name
   item.setdefault('device_name', r['device_name'] or item.get('hostname'))
   item.setdefault('status', item.get('lifecycle') or 'active')
   tel=one_source(c,'endpoint_telemetry',a['tenant_id'],'device_id',r['device_id']) or {}
   metrics=(tel.get('metrics') or {}) if isinstance(tel,dict) else {}
   if metrics.get('cpu_percent') is not None:item['cpu_percent']=metrics['cpu_percent']
   if metrics.get('disk_free_percent') is not None:item['disk_free_percent']=metrics['disk_free_percent']
   if metrics.get('memory_percent') is not None:item['memory_percent']=metrics['memory_percent']
   mdm=one_source(c,'mdm_managed_devices',a['tenant_id'],'device_id',r['device_id']) or {}
   if isinstance(mdm,dict) and mdm.get('complianceState'):item['compliance_state']=mdm['complianceState']
   out.append(item)
  return out
@app.get('/v1/devices/{device_id}/diagnostics')
def device_diagnostics(device_id:str,a=Depends(actor)):
 with dbc() as c:
  d=c.execute('SELECT * FROM devices WHERE tenant_id=? AND device_id=?',(a['tenant_id'],device_id)).fetchone()
  if not d:raise HTTPException(404,'Device not found')
  if d['owner_user_id']!=a['user_id'] and not staff(a):raise HTTPException(403,'Cannot inspect another user device')
  payload={'device':json.loads(d['attributes'])}
  for feed,key in [('mdm_managed_devices','device_id'),('endpoint_telemetry','device_id'),('device_patch_compliance','device_id')]:payload[feed]=one_source(c,feed,a['tenant_id'],key,device_id)
 return payload
@app.get('/v1/vpn/sessions')
def vpn_sessions(user_id:str|None=None,a=Depends(actor)):
 if user_id and user_id!=a['user_id'] and not staff(a):raise HTTPException(403,'Not authorised')
 with dbc() as c:rows=data_rows(c,'vpn_sessions',a['tenant_id'])
 uid=user_id or (None if staff(a) else a['user_id'])
 return [r for r in rows if uid is None or r['user_id']==uid][:100]
@app.get('/v1/tickets')
def tickets(status:str|None=None,limit:int=Query(100,ge=1,le=200),a=Depends(actor)):
 with dbc() as c:
  query='SELECT * FROM tickets WHERE tenant_id=?';args=[a['tenant_id']]
  if not can_manage_tickets(a):query+=' AND requester_id=?';args.append(a['user_id'])
  if status:query+=' AND status=?';args.append(status)
  query+=' ORDER BY created_at DESC LIMIT ?';args.append(limit)
  rows=c.execute(query,args).fetchall()
 return [json.loads(r['attributes'])|{'status':r['status']} for r in rows]
@app.get('/v1/tickets/{ticket_id}')
def ticket(ticket_id:str,a=Depends(actor)):
 with dbc() as c:r=c.execute('SELECT * FROM tickets WHERE tenant_id=? AND ticket_id=?',(a['tenant_id'],ticket_id)).fetchone()
 if not r:raise HTTPException(404,'Ticket not found')
 if r['requester_id']!=a['user_id'] and not can_manage_tickets(a):raise HTTPException(403,'Not authorised')
 return json.loads(r['attributes'])|{'status':r['status']}

class NewTicket(BaseModel):
 model_config=ConfigDict(extra='forbid')
 summary:str=Field(min_length=5,max_length=250)
 description:str=Field(min_length=5,max_length=4000)
 category:str=Field(pattern='^(identity|vpn|device|email|software|network|business_app|security|onboarding|offboarding|procurement|cloud_access)$')
 requester_id:str|None=None
 priority:str='P3'
@app.post('/v1/tickets')
def create_ticket(body:NewTicket,response:Response,idempotency_key:str|None=Header(default=None,alias='Idempotency-Key'),x_demo_fault:str|None=Header(default=None,alias='X-Demo-Fault'),a=Depends(actor)):
 if not idempotency_key or len(idempotency_key)>100:raise HTTPException(400,'Idempotency-Key required (max 100 characters)')
 if body.priority not in ('P1','P2','P3','P4'):raise HTTPException(422,'Invalid priority')
 if body.priority=='P1' and not can_manage_tickets(a):raise HTTPException(403,'P1 declaration requires an authorised IT role')
 target=body.requester_id or a['user_id']
 if target!=a['user_id'] and not can_manage_tickets(a):raise HTTPException(403,'Cannot create tickets for another user')
 request={'requester_id':target,'summary':body.summary,'description':body.description,'category':body.category,'priority':body.priority}
 digest=stable_hash(request)
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  u=c.execute('SELECT 1 FROM users WHERE tenant_id=? AND user_id=?',(a['tenant_id'],target)).fetchone()
  if not u:c.rollback();raise HTTPException(404,'Requester not found in your tenant')
  prev=c.execute('SELECT * FROM idempotency WHERE tenant_id=? AND actor_id=? AND operation=? AND key=?',(a['tenant_id'],a['user_id'],'tickets.create',idempotency_key)).fetchone()
  if prev:
   if prev['request_hash']!=digest:c.rollback();raise HTTPException(409,'Idempotency-Key used with different payload')
   result=json.loads(prev['result_json']);c.commit();response.status_code=200
   return result|{'idempotent_replay':True}
  if x_demo_fault=='rate_limit':c.rollback();raise HTTPException(429,'Simulated 429: retry with bounded backoff',headers={'Retry-After':'2'})
  ticket_id=a['tenant_id']+'-INC-NEW-'+uuid.uuid4().hex[:10]
  now=utcnow()
  row={'tenant_id':a['tenant_id'],'ticket_id':ticket_id,'requester_id':target,'summary':body.summary,'description':body.description,'category':body.category,'priority':body.priority,'status':'new','created_at':now,'updated_at':now,'source':'mock_itsm_api'}
  c.execute('INSERT INTO tickets VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(a['tenant_id'],ticket_id,target,None,body.summary,body.description,body.category,body.priority,'new',now,now,dumps(row)))
  result={'ticket_id':ticket_id,'tenant_id':a['tenant_id'],'requester_id':target,'status':'new','committed':True}
  c.execute('INSERT INTO idempotency VALUES(?,?,?,?,?,?,?)',(a['tenant_id'],a['user_id'],'tickets.create',idempotency_key,digest,dumps(result),now))
  audit(c,a,'ticket.create',ticket_id,'allow',{'idempotency_key_present':True})
  c.commit()
 if x_demo_fault=='timeout_after_commit':raise HTTPException(504,{'error':'simulated_timeout_after_successful_commit','status':'unknown_to_client','hint':'retry with identical Idempotency-Key or query ticket state; do not blindly create new request'})
 response.status_code=201
 return result|{'idempotent_replay':False}

class TicketUpdate(BaseModel):
 model_config=ConfigDict(extra='forbid')
 status:str|None=None
 assignee_id:str|None=None
 priority:str|None=None

VALID_STATUS_TRANSITIONS={
 'new':{'triaged','assigned','closed'},
 'triaged':{'assigned','new','closed'},
 'assigned':{'in_progress','triaged','closed'},
 'in_progress':{'pending_user','pending_vendor','escalated','resolved','assigned'},
 'pending_user':{'in_progress','resolved','escalated','closed'},
 'pending_vendor':{'in_progress','escalated','closed'},
 'escalated':{'in_progress','resolved','closed'},
 'resolved':{'closed','in_progress'},
 'closed':{'in_progress'}
}

@app.patch('/v1/tickets/{ticket_id}')
def update_ticket(ticket_id:str,body:TicketUpdate,a=Depends(actor)):
 if not can_manage_tickets(a):raise HTTPException(403,'Ticket management requires IT role')
 if body.priority and body.priority not in ('P1','P2','P3','P4'):raise HTTPException(422,'Invalid priority')
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  r=c.execute('SELECT * FROM tickets WHERE tenant_id=? AND ticket_id=?',(a['tenant_id'],ticket_id)).fetchone()
  if not r:c.rollback();raise HTTPException(404,'Ticket not found')
  attrs=json.loads(r['attributes'])
  changes={}
  if body.status:
   if body.status not in VALID_STATUS_TRANSITIONS.get(r['status'],set()):
    c.rollback();raise HTTPException(422,f"Invalid status transition from {r['status']} to {body.status}")
   changes['status']=body.status
  if body.assignee_id:
   if not c.execute('SELECT 1 FROM users WHERE tenant_id=? AND user_id=?',(a['tenant_id'],body.assignee_id)).fetchone():
    c.rollback();raise HTTPException(404,'Assignee not found in tenant')
   changes['assignee_id']=body.assignee_id
   attrs['assignee_id']=body.assignee_id
  if body.priority:
   changes['priority']=body.priority
   attrs['priority']=body.priority
  if changes:
   now=utcnow()
   attrs['updated_at']=now
   status=changes.get('status',r['status'])
   assignee=r['assignee_id']
   c.execute('UPDATE tickets SET status=?, assignee_id=?, attributes=?, updated_at=? WHERE tenant_id=? AND ticket_id=?',
    (status,assignee,dumps(attrs),now,a['tenant_id'],ticket_id))
   audit(c,a,'ticket.update',ticket_id,'allow',changes)
  c.commit()
 return {'ticket_id':ticket_id,'updated':True,'changes':changes}

class NewComment(BaseModel):
 model_config=ConfigDict(extra='forbid')
 body:str=Field(min_length=1,max_length=5000)
 visibility:str=Field(pattern='^(public|internal)$')

@app.post('/v1/tickets/{ticket_id}/comments',status_code=201)
def create_comment(ticket_id:str,body:NewComment,a=Depends(actor)):
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  r=c.execute('SELECT * FROM tickets WHERE tenant_id=? AND ticket_id=?',(a['tenant_id'],ticket_id)).fetchone()
  if not r:c.rollback();raise HTTPException(404,'Ticket not found')
  if r['requester_id']!=a['user_id'] and not can_manage_tickets(a):c.rollback();raise HTTPException(403,'Not authorised')
  if body.visibility=='internal' and not staff(a):c.rollback();raise HTTPException(403,'Employees cannot post internal comments')
  if not staff(a) and r['requester_id']!=a['user_id']:c.rollback();raise HTTPException(403,'Can only comment on own tickets')
  comment_id=a['tenant_id']+'-CMT-'+uuid.uuid4().hex[:12]
  now=utcnow()
  c.execute('INSERT INTO ticket_comments VALUES(?,?,?,?,?,?,?)',(a['tenant_id'],comment_id,ticket_id,a['user_id'],body.body,body.visibility,now))
  audit(c,a,'comment.create',comment_id,'allow',{'ticket_id':ticket_id,'visibility':body.visibility})
  c.commit()
 return {'comment_id':comment_id,'ticket_id':ticket_id,'author_id':a['user_id'],'body':body.body,'visibility':body.visibility,'created_at':now}

@app.get('/v1/tickets/{ticket_id}/comments')
def list_comments(ticket_id:str,a=Depends(actor)):
 with dbc() as c:
  r=c.execute('SELECT * FROM tickets WHERE tenant_id=? AND ticket_id=?',(a['tenant_id'],ticket_id)).fetchone()
  if not r:raise HTTPException(404,'Ticket not found')
  if r['requester_id']!=a['user_id'] and not can_manage_tickets(a):raise HTTPException(403,'Not authorised')
  rows=c.execute('SELECT * FROM ticket_comments WHERE tenant_id=? AND ticket_id=? ORDER BY created_at DESC',(a['tenant_id'],ticket_id)).fetchall()
 comments=[]
 for row in rows:
  if row['visibility']=='internal' and not staff(a):continue
  comments.append(dict(row))
 return comments

class IntegrationUpdate(BaseModel):
 model_config=ConfigDict(extra='forbid')
 enabled:bool|None=None
 connection_status:str|None=Field(default=None,pattern='^(connected_mock|disabled_mock)$')

@app.patch('/v1/admin/integrations/{integration_key}')
def update_integration(integration_key:str,body:IntegrationUpdate,a=Depends(actor)):
 if a['role']!='tenant_admin':raise HTTPException(403,'Admin only')
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  row=c.execute('SELECT record_json FROM integrations WHERE tenant_id=? AND integration_key=?',(a['tenant_id'],integration_key)).fetchone()
  if not row:c.rollback();raise HTTPException(404,'Integration not found')
  record=json.loads(row['record_json'])
  changes={}
  if body.enabled is not None:
   record['enabled']=body.enabled
   changes['enabled']=body.enabled
  if body.connection_status:
   record['connection_status']=body.connection_status
   changes['connection_status']=body.connection_status
  c.execute('UPDATE integrations SET record_json=? WHERE tenant_id=? AND integration_key=?',(dumps(record),a['tenant_id'],integration_key))
  audit(c,a,'integration.update',integration_key,'allow',changes)
  c.commit()
 return {'integration_key':integration_key,'updated':True,'changes':changes}

@app.post('/v1/admin/integrations/{integration_key}/test')
def test_integration(integration_key:str,a=Depends(actor)):
 if a['role']!='tenant_admin':raise HTTPException(403,'Admin only')
 with dbc() as c:
  row=c.execute('SELECT record_json FROM integrations WHERE tenant_id=? AND integration_key=?',(a['tenant_id'],integration_key)).fetchone()
  if not row:raise HTTPException(404,'Integration not found')
  record=json.loads(row['record_json'])
 if not record.get('enabled',True) or record.get('connection_status')=='disabled_mock':
  return {'integration_key':integration_key,'status':'degraded','message':'Integration is disabled'}
 return {'integration_key':integration_key,'status':'ok','last_healthcheck':utcnow()}

class NewEscalation(BaseModel):
 model_config=ConfigDict(extra='forbid')
 ticket_id:str|None=None
 reason:str=Field(min_length=10,max_length=2000)
 evidence_ids:list[str]|None=None
 severity:str|None=Field(default=None,pattern='^(low|medium|high|critical)$')

@app.post('/v1/security/escalations',status_code=201)
def create_escalation(body:NewEscalation,a=Depends(actor)):
 if a['role'] not in ('security_analyst','it_engineer'):raise HTTPException(403,'Security escalations require security_analyst or it_engineer role')
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  if body.ticket_id:
   t=c.execute('SELECT 1 FROM tickets WHERE tenant_id=? AND ticket_id=?',(a['tenant_id'],body.ticket_id)).fetchone()
   if not t:c.rollback();raise HTTPException(404,'Ticket not found in tenant')
  escalation_id=a['tenant_id']+'-ESC-'+uuid.uuid4().hex[:12]
  now=utcnow()
  evidence_json=dumps(body.evidence_ids or [])
  c.execute('INSERT INTO escalations VALUES(?,?,?,?,?,?,?,?,?,?)',
   (a['tenant_id'],escalation_id,body.ticket_id,a['user_id'],body.reason,evidence_json,body.severity or 'medium','open',now,now))
  audit(c,a,'escalation.create',escalation_id,'allow',{'ticket_id':body.ticket_id,'severity':body.severity})
  c.commit()
 return {'escalation_id':escalation_id,'tenant_id':a['tenant_id'],'ticket_id':body.ticket_id,'creator_id':a['user_id'],'reason':body.reason,'severity':body.severity or 'medium','status':'open','created_at':now}

@app.get('/v1/security/escalations')
def list_escalations(a=Depends(actor)):
 if a['role'] not in ('security_analyst','tenant_admin','it_manager'):raise HTTPException(403,'Security escalations require security_analyst, tenant_admin, or it_manager role')
 with dbc() as c:
  rows=c.execute('SELECT * FROM escalations WHERE tenant_id=? ORDER BY created_at DESC LIMIT 100',(a['tenant_id'],)).fetchall()
 return [{'escalation_id':r['escalation_id'],'ticket_id':r['ticket_id'],'creator_id':r['creator_id'],'reason':r['reason'],'evidence_ids':json.loads(r['evidence_ids']),'severity':r['severity'],'status':r['status'],'created_at':r['created_at']} for r in rows]

@app.get('/v1/knowledge/search')
def knowledge(q:str=Query(min_length=2),include_superseded:bool=False,a=Depends(actor)):
 if include_superseded and a['role']!='tenant_admin':raise HTTPException(403,'Archived KB requires tenant admin')
 with dbc() as c:rows=c.execute('SELECT * FROM knowledge_documents WHERE tenant_id=?',(a['tenant_id'],)).fetchall()
 terms={x.lower() for x in q.split() if len(x)>2};hits=[]
 for r in rows:
  if not visible_doc(a['role'],r['classification']):continue
  if not include_superseded and r['status']=='superseded':continue
  score=sum(3 for x in terms if x in r['title'].lower())+sum(1 for x in terms if x in r['body'].lower())
  if score<=0:continue
  hits.append(dict(document_id=r['document_id'],title=r['title'],version=r['version'],classification=r['classification'],status=r['status'],source=json.loads(r['metadata'])['source_system'],untrusted=r['status']=='unverified_vendor',score=score,excerpt=r['body'][:850]))
 return sorted(hits,key=lambda x:-x['score'])[:10]
@app.get('/v1/sources/{source_key}')
def source_records(source_key:str,limit:int=Query(50,ge=1,le=200),a=Depends(actor)):
 if a['role'] not in ('tenant_admin','security_analyst'):raise HTTPException(403,'Raw-source inspection restricted')
 if a['role']=='security_analyst' and not any(k in source_key for k in ('security','identity','vpn','application_audit','agent_')):raise HTTPException(403,'Source scope not authorised for security analyst')
 with dbc() as c:
  rows=c.execute('SELECT json_record FROM source_records WHERE tenant_id=? AND source_key=? ORDER BY ordinal LIMIT ?',(a['tenant_id'],source_key,limit)).fetchall()
 return [json.loads(r['json_record']) for r in rows]
@app.get('/v1/admin/integrations')
def connections(a=Depends(actor)):
 if a['role']!='tenant_admin':raise HTTPException(403,'Admin only')
 with dbc() as c:rows=c.execute('SELECT record_json FROM integrations WHERE tenant_id=?',(a['tenant_id'],)).fetchall()
 return [json.loads(r['record_json']) for r in rows]
@app.get('/v1/admin/policy')
def admin_policy(a=Depends(actor)):
 if a['role'] not in ('tenant_admin','it_manager'):raise HTTPException(403,'Policy visibility restricted')
 with dbc() as c:r=c.execute('SELECT body_json FROM policies WHERE tenant_id=?',(a['tenant_id'],)).fetchone()
 return json.loads(r['body_json'])
@app.get('/v1/analytics')
def analytics(a=Depends(actor)):
 if a['role'] not in ('it_manager','tenant_admin','it_engineer'):raise HTTPException(403,'Operations access required')
 with dbc() as c:
  rows=c.execute('SELECT status,COUNT(*) n FROM tickets WHERE tenant_id=? GROUP BY status',(a['tenant_id'],)).fetchall()
  total=sum(x['n'] for x in rows)
  by_priority=c.execute('SELECT priority,COUNT(*) n FROM tickets WHERE tenant_id=? GROUP BY priority',(a['tenant_id'],)).fetchall()
 return {'total_tickets':total,'status_counts':{x['status']:x['n'] for x in rows},'priority_counts':{x['priority']:x['n'] for x in by_priority},'note':'Calculated from the mutable SQLite mock; this is not a production automation resolution rate'}

class NewApproval(BaseModel):
 model_config=ConfigDict(extra='forbid')
 action_type:str
 target_user_id:str
 device_id:str|None=None
 rationale:str=Field(min_length=5,max_length=1000)
@app.post('/v1/approvals',status_code=201)
def create_approval(b:NewApproval,a=Depends(actor)):
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  row=c.execute('SELECT body_json FROM policies WHERE tenant_id=?',(a['tenant_id'],)).fetchone()
  cfg=json.loads(row['body_json']);rule=cfg['policies'].get(b.action_type)
  if not rule or rule['mode']!='human_approval':c.rollback();raise HTTPException(403,'Action not eligible for helpdesk approval')
  if b.target_user_id!=a['user_id'] and a['role'] not in ('it_engineer','security_analyst'):c.rollback();raise HTTPException(403,'Cannot propose an action against another account')
  if not c.execute('SELECT 1 FROM users WHERE tenant_id=? AND user_id=?',(a['tenant_id'],b.target_user_id)).fetchone():c.rollback();raise HTTPException(404,'Target account not in tenant')
  if b.action_type=='vpn_certificate_renewal':
   d=c.execute('SELECT owner_user_id FROM devices WHERE tenant_id=? AND device_id=?',(a['tenant_id'],b.device_id)).fetchone()
   if not d or d['owner_user_id']!=b.target_user_id:c.rollback();raise HTTPException(422,'Device must be assigned to target user')
  payload={'action':b.action_type,'tenant_id':a['tenant_id'],'target_user_id':b.target_user_id,'device_id':b.device_id,'request_version':1}
  aid=a['tenant_id']+'-APR-NEW-'+uuid.uuid4().hex[:10];now=datetime.now(timezone.utc)
  expires=(now+timedelta(minutes=rule.get('expires_minutes',30))).isoformat().replace('+00:00','Z')
  c.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(a['tenant_id'],aid,a['user_id'],None,b.action_type,dumps(payload),stable_hash(payload),'pending',utcnow(),expires,None,None))
  audit(c,a,'approval.request',aid,'allow',{'action':b.action_type})
  c.commit()
 return {'approval_id':aid,'status':'pending','action':payload,'expires_at':expires}
class Decision(BaseModel):
 decision:str=Field(pattern='^(approved|rejected)$')
 reason:str=Field(min_length=5,max_length=500)
@app.post('/v1/approvals/{approval_id}/decision')
def decide(approval_id:str,b:Decision,a=Depends(actor)):
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  r=c.execute('SELECT * FROM approvals WHERE tenant_id=? AND approval_id=?',(a['tenant_id'],approval_id)).fetchone()
  if not r:c.rollback();raise HTTPException(404,'Approval not found')
  if r['requester_id']==a['user_id']:c.rollback();raise HTTPException(403,'Self approval prohibited')
  cfg=json.loads(c.execute('SELECT body_json FROM policies WHERE tenant_id=?',(a['tenant_id'],)).fetchone()['body_json'])
  allowed=cfg['policies'].get(r['action_type'],{}).get('approver_roles',[])
  if a['role'] not in allowed:c.rollback();raise HTTPException(403,'Role not approved for this action and tenant')
  if r['status']!='pending':c.rollback();raise HTTPException(409,'Approval no longer pending')
  if parse_date(r['expires_at'])<=datetime.now(timezone.utc):c.rollback();raise HTTPException(409,'Approval expired')
  c.execute('UPDATE approvals SET status=?, approver_id=?, decided_at=?, reason=? WHERE tenant_id=? AND approval_id=?',(b.decision,a['user_id'],utcnow(),b.reason,a['tenant_id'],approval_id))
  audit(c,a,'approval.'+b.decision,approval_id,'allow',{'reason':b.reason})
  c.commit()
 return {'approval_id':approval_id,'decision':b.decision,'decided_by':a['user_id']}
@app.post('/v1/approvals/{approval_id}/execute')
def execute(approval_id:str,a=Depends(actor)):
 with dbc() as c:
  c.execute('BEGIN IMMEDIATE')
  r=c.execute('SELECT * FROM approvals WHERE tenant_id=? AND approval_id=?',(a['tenant_id'],approval_id)).fetchone()
  if not r:c.rollback();raise HTTPException(404,'Approval not found')
  # a trusted worker identity is preferable in production. In this demo only the specific approving engineer may execute.
  if r['status']!='approved' or r['approver_id']!=a['user_id']:c.rollback();raise HTTPException(403,'Approved action and original approver identity required')
  if parse_date(r['expires_at'])<=datetime.now(timezone.utc):c.rollback();raise HTTPException(409,'Approval expired')
  payload=json.loads(r['action_json'])
  if stable_hash(payload)!=r['action_hash']:c.rollback();raise HTTPException(409,'Action payload hash mismatch')
  actionid='EXEC-'+approval_id
  prior=c.execute('SELECT result_json FROM actions WHERE tenant_id=? AND action_id=?',(a['tenant_id'],actionid)).fetchone()
  if prior:c.commit();return json.loads(prior['result_json'])|{'idempotent_replay':True}
  if payload['action']=='vpn_certificate_renewal':
   d=one_source(c,'mdm_managed_devices',a['tenant_id'],'device_id',payload['device_id'])
   if not d or d['complianceState']!='compliant':c.rollback();raise HTTPException(409,'Device compliance prerequisite failed; requires investigation')
  elif payload['action']=='identity_account_unlock':
   current=c.execute('SELECT ordinal,json_record FROM source_records WHERE tenant_id=? AND source_key=?',(a['tenant_id'],'identity_directory')).fetchall()
   changed=False
   for it in current:
    account=json.loads(it['json_record'])
    if account['employee_id']==payload['target_user_id']:
     account['account_state']='active';account['accountEnabled']=True
     c.execute('UPDATE source_records SET json_record=? WHERE tenant_id=? AND source_key=? AND ordinal=?',(dumps(account),a['tenant_id'],'identity_directory',it['ordinal']))
     changed=True;break
   if not changed:c.rollback();raise HTTPException(404,'Account no longer exists')
  else:c.rollback();raise HTTPException(403,'Unsupported action')
  result={'action_id':actionid,'status':'succeeded_mock','action_type':payload['action'],'target_user_id':payload['target_user_id'],'executed_at':utcnow(),'real_enterprise_mutation':False}
  c.execute('INSERT INTO actions VALUES(?,?,?,?,?,?,?,?)',(a['tenant_id'],actionid,approval_id,payload['action'],payload['target_user_id'],'succeeded_mock',utcnow(),dumps(result)))
  audit(c,a,'action.execute',actionid,'allow',{'approval':approval_id})
  c.commit()
 return result|{'idempotent_replay':False}
@app.get('/v1/audit')
def audits(limit:int=Query(50,ge=1,le=200),a=Depends(actor)):
 if a['role'] not in ('tenant_admin','security_analyst'):raise HTTPException(403,'Audit visibility restricted')
 with dbc() as c:rows=c.execute('SELECT * FROM audit_log WHERE tenant_id=? ORDER BY id DESC LIMIT ?',(a['tenant_id'],limit)).fetchall()
 return [dict(r) for r in rows]
@app.get('/v1/approvals')
def list_approvals(status:str|None=None,a=Depends(actor)):
 with dbc() as c:
  rows=c.execute('SELECT * FROM approvals WHERE tenant_id=? ORDER BY created_at DESC LIMIT 100',(a['tenant_id'],)).fetchall()
  cfg=json.loads(c.execute('SELECT body_json FROM policies WHERE tenant_id=?',(a['tenant_id'],)).fetchone()['body_json'])
 result=[]
 for r in rows:
  eligible=a['role'] in cfg['policies'].get(r['action_type'],{}).get('approver_roles',[])
  if r['requester_id']!=a['user_id'] and not eligible:continue
  if status and r['status']!=status:continue
  result.append({'approval_id':r['approval_id'],'requester_id':r['requester_id'],'action_type':r['action_type'],'status':r['status'],'action':json.loads(r['action_json']),'created_at':r['created_at'],'expires_at':r['expires_at'],'reason':r['reason'],'eligible_to_review':eligible and r['requester_id']!=a['user_id']})
 return result
@app.get('/v1/agent/executions')
def agent_traces(a=Depends(actor)):
 with dbc() as c:
  rows=data_rows(c,'agent_executions',a['tenant_id'])
 if a['role'] not in ('it_engineer','it_manager','tenant_admin','security_analyst'):
  rows=[r for r in rows if r['principal_id']==a['user_id']]
 return {'records':rows[:50],'warning':'These are synthetic seed execution records, not real Bedrock/AgentCore traces.'}
@app.get('/v1/services/outages')
def service_outages(a=Depends(actor)):
 with dbc() as c:rows=data_rows(c,'service_health_outages',a['tenant_id'])
 return [{k:r[k] for k in ('outage_id','service_key','severity','status','started_at','symptom','impacted_sites')} for r in rows]
@app.get('/v1/service-catalog')
def service_catalog(a=Depends(actor)):
 with dbc() as c:rows=data_rows(c,'service_catalog',a['tenant_id'])
 return [{k:r[k] for k in ('service_id','service_key','name','tier','self_service_available','is_enabled')} for r in rows]
