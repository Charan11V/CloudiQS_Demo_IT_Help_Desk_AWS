# Complete Raw Source Catalog

47 source feeds; each has `data/raw/<name>/northstar.jsonl` and `/beacon.jsonl`. Independent feed snapshots are deliberately not a single cleaned customer record.

| Feed | Records | Owner | Cadence | Data sensitivity |
|---|---:|---|---|---|
| `hris_people` | 40 | HR | hourly | restricted |
| `identity_directory` | 40 | IAM | event_stream | restricted |
| `identity_signins` | 160 | Enterprise IT | event_stream | restricted |
| `identity_mfa_factors` | 40 | Enterprise IT | daily | restricted |
| `saas_entitlements` | 148 | Enterprise IT | event_stream | internal |
| `asset_register` | 50 | Enterprise IT | every_15_minutes | internal |
| `cmdb_ci` | 50 | Enterprise IT | manual_publish | internal |
| `mdm_managed_devices` | 50 | Endpoint Engineering | manual_publish | internal |
| `endpoint_telemetry` | 50 | Enterprise IT | every_15_minutes | internal |
| `device_patch_compliance` | 50 | Enterprise IT | every_15_minutes | internal |
| `installed_software` | 182 | Enterprise IT | event_stream | internal |
| `asset_procurement` | 50 | Enterprise IT | every_15_minutes | internal |
| `device_warranty` | 50 | Enterprise IT | event_stream | internal |
| `vpn_sessions` | 130 | Network Operations | daily | internal |
| `dns_queries` | 130 | Enterprise IT | hourly | internal |
| `wifi_auth_events` | 130 | Enterprise IT | event_stream | internal |
| `dhcp_leases` | 130 | Enterprise IT | manual_publish | internal |
| `network_change_log` | 10 | Enterprise IT | event_stream | internal |
| `service_catalog` | 24 | Enterprise IT | every_15_minutes | internal |
| `service_request_forms` | 24 | Enterprise IT | hourly | internal |
| `sla_policies` | 8 | Enterprise IT | event_stream | internal |
| `itsm_tickets` | 80 | IT Service Desk | hourly | internal |
| `itsm_comments` | 240 | Enterprise IT | hourly | internal |
| `itsm_history` | 240 | Enterprise IT | daily | internal |
| `itsm_problems` | 6 | Enterprise IT | daily | internal |
| `itsm_changes` | 8 | Enterprise IT | daily | internal |
| `change_approvals` | 8 | Enterprise IT | daily | internal |
| `service_health_outages` | 8 | Enterprise IT | event_stream | internal |
| `oncall_rotations` | 8 | Enterprise IT | every_15_minutes | internal |
| `security_findings` | 23 | Security Operations | daily | restricted |
| `csat_surveys` | 10 | Enterprise IT | event_stream | internal |
| `outbound_notifications` | 8 | Enterprise IT | hourly | internal |
| `collaboration_messages` | 13 | Enterprise IT | every_15_minutes | internal |
| `email_transport_events` | 9 | Enterprise IT | hourly | internal |
| `hr_joiner_leaver_tasks` | 8 | Enterprise IT | manual_publish | internal |
| `saas_licenses` | 14 | Enterprise IT | every_15_minutes | internal |
| `software_access_requests` | 6 | Enterprise IT | manual_publish | internal |
| `integration_api_errors` | 27 | Enterprise IT | every_15_minutes | internal |
| `vendor_status` | 8 | Enterprise IT | manual_publish | internal |
| `agent_usage_and_costs` | 28 | Cloud FinOps | manual_publish | internal |
| `application_audit` | 17 | Compliance | daily | internal |
| `tenant_policies` | 2 | Security Architecture | manual_publish | internal |
| `role_permissions` | 16 | Enterprise IT | daily | internal |
| `integration_registry` | 16 | Enterprise IT | every_15_minutes | internal |
| `human_approvals` | 14 | IT Operations | hourly | internal |
| `agent_executions` | 14 | Enterprise IT | manual_publish | internal |
| `knowledge_index` | 27 | Knowledge Management | manual_publish | mixed_restricted |
