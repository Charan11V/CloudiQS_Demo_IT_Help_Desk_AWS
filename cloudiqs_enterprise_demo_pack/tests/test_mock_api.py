import shutil
import sqlite3
import pytest
from fastapi.testclient import TestClient
from mock_api import app as api
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture()
def client(tmp_path,monkeypatch):
 target=tmp_path/'test.sqlite';shutil.copyfile(ROOT/'data'/'canonical'/'enterprise.sqlite',target)
 monkeypatch.setattr(api,'DB',target)
 return TestClient(api.app)
def hdr(token):return {'Authorization':f'Bearer {token}'}
def new_ticket():return {'summary':'VPN fails from my home office','description':'An access error appears after login; please investigate the problem.','category':'vpn'}
def test_health_and_identity(client):
 assert client.get('/health').json()['mode']=='synthetic_mock_only'
 u=client.get('/v1/me',headers=hdr('northstar-asha'));assert u.status_code==200 and u.json()['role']=='employee'
 assert client.get('/v1/me').status_code==401
 assert client.get('/v1/me',headers=hdr('northstar-omar-terminated')).status_code==401

def test_company_isolation_and_no_header_spoof(client):
 r=client.get('/v1/tickets/beacon-INC-0001',headers=hdr('northstar-rahul')|{'X-Tenant-ID':'beacon'});assert r.status_code==404
 r=client.get('/v1/identity/accounts/beacon-EMP-0001',headers=hdr('northstar-rahul'));assert r.status_code==404
 r=client.get('/v1/tickets',headers=hdr('northstar-asha'));assert r.status_code==200
 assert all(x['tenant_id']=='northstar' and x['requester_id']=='northstar-EMP-0001' for x in r.json())
 r=client.get('/v1/devices/beacon-DEV-0001/diagnostics',headers=hdr('northstar-vikram'));assert r.status_code==404
 r=client.get('/v1/tickets',headers=hdr('beacon-neha'));assert all(x['tenant_id']=='beacon' for x in r.json())

def test_sensitive_knowledge_acl(client):
 emp=client.get('/v1/knowledge/search?q=MFA',headers=hdr('northstar-asha')).json()
 assert all(x['classification']=='employees' for x in emp)
 sec=client.get('/v1/knowledge/search?q=MFA',headers=hdr('northstar-arjun-security')).json()
 assert any(x['classification']=='security' for x in sec)
 assert client.get('/v1/knowledge/search?q=VPN&include_superseded=true',headers=hdr('northstar-asha')).status_code==403

def test_ticket_idempotency_and_timeout_after_commit(client):
 key='one-day-test-001';h=hdr('northstar-asha')|{'Idempotency-Key':key,'X-Demo-Fault':'timeout_after_commit'}
 first=client.post('/v1/tickets',headers=h,json=new_ticket());assert first.status_code==504
 second=client.post('/v1/tickets',headers=hdr('northstar-asha')|{'Idempotency-Key':key},json=new_ticket())
 assert second.status_code==200 and second.json()['idempotent_replay']
 with sqlite3.connect(api.DB) as c:
  assert c.execute("select count(*) from idempotency where key=?",(key,)).fetchone()[0]==1
  tid=second.json()['ticket_id']
  assert c.execute('select count(*) from tickets where ticket_id=?',(tid,)).fetchone()[0]==1
 conflict=client.post('/v1/tickets',headers=hdr('northstar-asha')|{'Idempotency-Key':key},json=new_ticket()|{'summary':'A different request'})
 assert conflict.status_code==409

def test_permissions_on_ticket_creation(client):
 r=client.post('/v1/tickets',headers=hdr('northstar-asha')|{'Idempotency-Key':'self-other'},json=new_ticket()|{'requester_id':'northstar-EMP-0003'})
 assert r.status_code==403
 assert client.post('/v1/tickets',headers=hdr('northstar-asha'),json=new_ticket()).status_code==400
 assert client.post('/v1/tickets',headers=hdr('northstar-asha')|{'Idempotency-Key':'rate'},json=new_ticket()|{'priority':'P1'}).status_code==403

def test_approval_separation_and_execution(client):
 payload={'action_type':'identity_account_unlock','target_user_id':'northstar-EMP-0001','rationale':'Locked account verified from identity logs'}
 result=client.post('/v1/approvals',headers=hdr('northstar-asha'),json=payload)
 assert result.status_code==201,result.text
 aid=result.json()['approval_id']
 assert client.post(f'/v1/approvals/{aid}/decision',headers=hdr('northstar-asha'),json={'decision':'approved','reason':'Self approval attempt'}).status_code==403
 assert client.post(f'/v1/approvals/{aid}/decision',headers=hdr('northstar-vikram'),json={'decision':'approved','reason':'Admin cannot approve as engineer'}).status_code==403
 dec=client.post(f'/v1/approvals/{aid}/decision',headers=hdr('northstar-rahul'),json={'decision':'approved','reason':'Verified requester identity and ticket evidence'})
 assert dec.status_code==200,dec.text
 assert client.post(f'/v1/approvals/{aid}/execute',headers=hdr('northstar-asha')).status_code==403
 exe=client.post(f'/v1/approvals/{aid}/execute',headers=hdr('northstar-rahul'));assert exe.status_code==200,exe.text
 replay=client.post(f'/v1/approvals/{aid}/execute',headers=hdr('northstar-rahul'));assert replay.status_code==200 and replay.json()['idempotent_replay']
 acc=client.get('/v1/identity/accounts/northstar-EMP-0001',headers=hdr('northstar-asha'));assert acc.json()['account_state']=='active'
 assert client.post('/v1/approvals',headers=hdr('northstar-asha'),json=payload|{'action_type':'mfa_reset'}).status_code==403

def test_vpn_non_compliance_enforced_at_action_time(client):
 a={'action_type':'vpn_certificate_renewal','target_user_id':'northstar-EMP-0001','device_id':'northstar-DEV-0001','rationale':'Certificate expired; IT action requested'}
 r=client.post('/v1/approvals',headers=hdr('northstar-asha'),json=a);assert r.status_code==201
 aid=r.json()['approval_id']
 assert client.post(f'/v1/approvals/{aid}/decision',headers=hdr('northstar-rahul'),json={'decision':'approved','reason':'Reviewed associated certificate evidence'}).status_code==200
 assert client.post(f'/v1/approvals/{aid}/execute',headers=hdr('northstar-rahul')).status_code==409

def test_source_and_analytics_role_scope(client):
 assert client.get('/v1/sources/hris_people',headers=hdr('northstar-asha')).status_code==403
 assert client.get('/v1/admin/integrations',headers=hdr('northstar-asha')).status_code==403
 assert client.get('/v1/analytics',headers=hdr('northstar-priya')).status_code==200
 result=client.get('/v1/analytics',headers=hdr('beacon-james')).json();assert result['total_tickets']==20


def test_approval_visibility_and_different_tenant_rules(client):
 a=client.post('/v1/approvals',headers=hdr('beacon-neha'),json={'action_type':'identity_account_unlock','target_user_id':'beacon-EMP-0001','rationale':'Employee account recovery after verification'})
 assert a.status_code==201
 aid=a.json()['approval_id']
 assert client.post(f'/v1/approvals/{aid}/decision',headers=hdr('beacon-david'),json={'decision':'approved','reason':'Reviewed user evidence'}).status_code==403
 assert client.post(f'/v1/approvals/{aid}/decision',headers=hdr('beacon-noah-security'),json={'decision':'approved','reason':'Completed required identity check'}).status_code==200
 assert all(x['tenant_id']=='beacon' for x in client.get('/v1/service-catalog',headers=hdr('beacon-neha')).json() if 'tenant_id' in x)
 visible=client.get('/v1/approvals',headers=hdr('northstar-asha')).json()
 assert all(x['requester_id']=='northstar-EMP-0001' for x in visible)
 assert client.get('/v1/agent/executions',headers=hdr('northstar-asha')).status_code==200

def test_ticket_update_by_it_staff(client):
 # Create a fresh ticket for testing
 ticket=client.post('/v1/tickets',headers=hdr('northstar-rahul')|{'Idempotency-Key':'update-test-001'},json=new_ticket())
 assert ticket.status_code==201
 assert ticket.json()['assignee_id']=='northstar-EMP-0002'
 assert ticket.json()['status']=='assigned'
 sec=client.post('/v1/tickets',headers=hdr('northstar-rahul')|{'Idempotency-Key':'update-test-sec'},json=new_ticket()|{'category':'security','summary':'Unexpected MFA prompt today'})
 assert sec.status_code==201
 assert sec.json()['assignee_id']=='northstar-EMP-0011'
 ident=client.post('/v1/tickets',headers=hdr('northstar-rahul')|{'Idempotency-Key':'update-test-id'},json=new_ticket()|{'category':'identity','summary':'Account locked after sign-in attempts'})
 assert ident.status_code==201 and ident.json()['assignee_id']=='northstar-EMP-0002'
 beacon=client.post('/v1/tickets',headers=hdr('beacon-neha')|{'Idempotency-Key':'update-test-beacon'},json=new_ticket())
 assert beacon.status_code==201 and beacon.json()['assignee_id']=='beacon-EMP-0002'
 ticket_id=ticket.json()['ticket_id']
 # IT engineer can PATCH ticket status from new to triaged
 update=client.patch(f'/v1/tickets/{ticket_id}',headers=hdr('northstar-rahul'),json={'status':'triaged'})
 assert update.status_code==200,update.text
 assert update.json()['changes']['status']=='triaged'
 # Employee cannot update tickets
 assert client.patch(f'/v1/tickets/{ticket_id}',headers=hdr('northstar-asha'),json={'status':'closed'}).status_code==403
 # Invalid status transition from triaged to resolved (must go through assigned/in_progress)
 bad_transition=client.patch(f'/v1/tickets/{ticket_id}',headers=hdr('northstar-rahul'),json={'status':'resolved'})
 assert bad_transition.status_code==422
 # Valid transition from triaged to assigned with assignee
 good_transition=client.patch(f'/v1/tickets/{ticket_id}',headers=hdr('northstar-rahul'),json={'status':'assigned','assignee_id':'northstar-EMP-0002','priority':'P2'})
 assert good_transition.status_code==200
 assert good_transition.json()['changes']['status']=='assigned'
 assert good_transition.json()['changes']['assignee_id']=='northstar-EMP-0002'

def test_cross_tenant_ticket_404(client):
 # Northstar user cannot access Beacon ticket
 r=client.get('/v1/tickets/beacon-INC-0001',headers=hdr('northstar-rahul'))
 assert r.status_code==404
 # Northstar IT cannot update Beacon ticket
 r=client.patch('/v1/tickets/beacon-INC-0001',headers=hdr('northstar-rahul'),json={'status':'closed'})
 assert r.status_code==404
 # Beacon user can access their own tickets
 beacon_tickets=client.get('/v1/tickets',headers=hdr('beacon-neha')).json()
 assert all(x['tenant_id']=='beacon' for x in beacon_tickets)

def test_ticket_comments_employee_cannot_post_internal(client):
 # Create a ticket as employee
 ticket=client.post('/v1/tickets',headers=hdr('northstar-asha')|{'Idempotency-Key':'comment-test-001'},json=new_ticket())
 assert ticket.status_code==201
 ticket_id=ticket.json()['ticket_id']
 # Employee can post public comment
 public_comment=client.post(f'/v1/tickets/{ticket_id}/comments',headers=hdr('northstar-asha'),json={'body':'I also tried rebooting my router','visibility':'public'})
 assert public_comment.status_code==201,public_comment.text
 # Employee CANNOT post internal comment
 internal_comment=client.post(f'/v1/tickets/{ticket_id}/comments',headers=hdr('northstar-asha'),json={'body':'Internal note','visibility':'internal'})
 assert internal_comment.status_code==403
 # IT staff CAN post internal comment
 staff_internal=client.post(f'/v1/tickets/{ticket_id}/comments',headers=hdr('northstar-rahul'),json={'body':'Internal IT note','visibility':'internal'})
 assert staff_internal.status_code==201
 # Employee can see their own public comments but not internal
 comments=client.get(f'/v1/tickets/{ticket_id}/comments',headers=hdr('northstar-asha')).json()
 assert len(comments)==1 and comments[0]['visibility']=='public'
 # IT staff can see all comments
 all_comments=client.get(f'/v1/tickets/{ticket_id}/comments',headers=hdr('northstar-rahul')).json()
 assert len(all_comments)==2

def test_admin_can_disable_integration(client):
 # Employee cannot access integrations
 assert client.get('/v1/admin/integrations',headers=hdr('northstar-asha')).status_code==403
 # Admin can list integrations
 integrations=client.get('/v1/admin/integrations',headers=hdr('northstar-vikram')).json()
 assert len(integrations)>0
 integration_key=integrations[0]['integration_key']
 # Admin can disable integration
 update=client.patch(f'/v1/admin/integrations/{integration_key}',headers=hdr('northstar-vikram'),json={'enabled':False})
 assert update.status_code==200,update.text
 assert update.json()['changes']['enabled']==False
 # Admin can update connection_status
 status_update=client.patch(f'/v1/admin/integrations/{integration_key}',headers=hdr('northstar-vikram'),json={'connection_status':'disabled_mock'})
 assert status_update.status_code==200
 # Test disabled integration
 test_result=client.post(f'/v1/admin/integrations/{integration_key}/test',headers=hdr('northstar-vikram')).json()
 assert test_result['status']=='degraded'
 # Re-enable and test
 client.patch(f'/v1/admin/integrations/{integration_key}',headers=hdr('northstar-vikram'),json={'enabled':True,'connection_status':'connected_mock'})
 test_ok=client.post(f'/v1/admin/integrations/{integration_key}/test',headers=hdr('northstar-vikram')).json()
 assert test_ok['status']=='ok'
 # Non-admin cannot update
 assert client.patch(f'/v1/admin/integrations/{integration_key}',headers=hdr('northstar-asha'),json={'enabled':True}).status_code==403

def test_security_escalations(client):
 # Create ticket first
 ticket=client.post('/v1/tickets',headers=hdr('northstar-asha')|{'Idempotency-Key':'escalation-test-001'},json=new_ticket())
 ticket_id=ticket.json()['ticket_id']
 # Security analyst can create escalation
 escalation=client.post('/v1/security/escalations',headers=hdr('northstar-arjun-security'),json={'ticket_id':ticket_id,'reason':'Potential security incident detected in VPN logs','severity':'high','evidence_ids':['LOG-001','LOG-002']})
 assert escalation.status_code==201,escalation.text
 assert escalation.json()['severity']=='high'
 # IT engineer can also create escalation
 it_escalation=client.post('/v1/security/escalations',headers=hdr('northstar-rahul'),json={'reason':'Suspicious activity pattern detected','severity':'medium'})
 assert it_escalation.status_code==201
 # Employee cannot create escalation
 assert client.post('/v1/security/escalations',headers=hdr('northstar-asha'),json={'reason':'Something seems wrong','severity':'low'}).status_code==403
 # Security analyst can list escalations
 escalations=client.get('/v1/security/escalations',headers=hdr('northstar-arjun-security')).json()
 assert len(escalations)>=2
 # IT manager can list escalations
 assert client.get('/v1/security/escalations',headers=hdr('northstar-priya')).status_code==200
 # Employee cannot list escalations
 assert client.get('/v1/security/escalations',headers=hdr('northstar-asha')).status_code==403
