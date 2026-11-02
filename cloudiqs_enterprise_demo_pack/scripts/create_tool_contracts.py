from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
# Contracts declare intended tool abstraction, NOT proof those endpoints are implemented.
tools=[
('identity_get_self','identity','read','/v1/identity/accounts/{user_id}','employee,IT','self_or_authorised_support','identity_directory'),
('identity_get_signin_history','identity','read','/v1/identity/signins/{user_id}','employee,IT','self_or_authorised_support','identity_signins'),
('identity_request_unlock','identity','approval','/v1/approvals','employee,IT','human_required','identity_directory,tenant_policies'),
('identity_reset_mfa','identity','forbidden',None,'none','always_denied','identity_mfa_factors,tenant_policies'),
('identity_grant_admin','identity','forbidden',None,'none','always_denied','saas_entitlements,tenant_policies'),
('asset_get_my_devices','device','read','/v1/devices','employee,IT','self_or_authorised_support','asset_register'),
('device_get_diagnostics','device','read','/v1/devices/{device_id}/diagnostics','employee,IT','assigned_or_authorised_support','mdm_managed_devices,endpoint_telemetry,device_patch_compliance'),
('device_request_vpn_cert_renewal','device','approval','/v1/approvals','employee,IT','requires_approval_and_compliance','mdm_managed_devices,vpn_sessions'),
('device_remote_wipe','device','forbidden',None,'none','always_denied','tenant_policies'),
('vpn_get_sessions','network','read','/v1/vpn/sessions','employee,IT','self_or_authorised_support','vpn_sessions'),
('vpn_query_gateway_health','network','read',None,'IT','tenant_scoped','service_health_outages,vendor_status'),
('wifi_get_radius_errors','network','read',None,'IT','device_scoped','wifi_auth_events'),
('dns_lookup_history','network','read',None,'IT','device_scoped','dns_queries'),
('itsm_get_ticket','itsm','read','/v1/tickets/{ticket_id}','employee,IT','own_or_tenant_IT','itsm_tickets'),
('itsm_list_tickets','itsm','read','/v1/tickets','employee,IT','own_or_tenant_IT','itsm_tickets'),
('itsm_create_ticket','itsm','mutate','/v1/tickets','employee,IT','idempotency_key_required','itsm_tickets'),
('itsm_assign_ticket','itsm','mutate',None,'IT','manager_permission_and_audit','itsm_tickets'),
('itsm_get_sla','itsm','read',None,'IT','tenant_scoped','sla_policies,itsm_tickets'),
('knowledge_search','knowledge','read','/v1/knowledge/search','employee,IT','filter_ACL_before_retrieval','knowledge_index'),
('knowledge_get_current_policy','knowledge','read',None,'employee,IT','only_valid_current_policy','knowledge_index,tenant_policies'),
('security_get_findings','security','read',None,'Security','security_analyst_role_only','security_findings'),
('security_escalate','security','notify',None,'IT,Security','oncall_and_ticket','security_findings,oncall_rotations'),
('hr_lookup_lifecycle','people','read',None,'HR,Security','privileged_lifecycle_access','hris_people,hr_joiner_leaver_tasks'),
('software_get_license_seats','software','read',None,'IT','tenant_scoped','saas_licenses'),
('software_request_access','software','approval',None,'employee','manager_approval_required','software_access_requests'),
('approval_propose_action','governance','approval','/v1/approvals','employee,IT','immutable_payload','tenant_policies,human_approvals'),
('approval_decide_action','governance','mutate','/v1/approvals/{approval_id}/decision','authorised_approver','no_self_approval','tenant_policies,human_approvals'),
('approval_execute_action','governance','mutate','/v1/approvals/{approval_id}/execute','approved_executor','expiry_hash_and_prerequisites','human_approvals'),
('admin_get_integrations','admin','read','/v1/admin/integrations','tenant_admin','tenant_admin_only','integration_registry'),
('admin_get_policy','admin','read','/v1/admin/policy','tenant_admin,IT_manager','tenant_scoped','tenant_policies'),
('analytics_get_ticket_counts','analytics','read','/v1/analytics','IT_manager,IT','tenant_scoped','itsm_tickets'),
('audit_get_execution_history','audit','read','/v1/audit','tenant_admin,Security','tenant_scoped_and_redacted','application_audit')]
out=[]
for i,(name,domain,kind,endpoint,roles,guardrail,sources) in enumerate(tools,1):
 out.append({'tool_id':f'TOOL-{i:03d}','name':name,'domain':domain,'action_class':kind,'mock_api_endpoint':endpoint,'endpoint_implemented':endpoint is not None,'intended_callers':roles,'required_authorisation':guardrail,'data_sources':[s.strip() for s in sources.split(',')],'identity_binding':'authenticated_actor.tenant_id + verified_user_id','audit_required':True,'input_schema_outline':{'type':'object','additionalProperties':False,'properties':{'target_id':{'type':'string'},'reason':{'type':'string'},'idempotency_key':{'type':'string'}}},'failure_behaviours':['401_unauthenticated','403_unauthorised','404_wrong_tenant','429_rate_limited','504_unknown_outcome_on_write' if kind=='mutate' else '503_unavailable'],'notes':'Proposed agent-tool contract; only listed mock_api_endpoint routes exist in this pack.'})
(ROOT/'data'/'agent_tool_contracts.json').write_text(json.dumps(out,indent=2)+'\n')
print(len(out),'agent tool contracts;',sum(1 for r in out if r['endpoint_implemented']),'with corresponding HTTP route templates')
