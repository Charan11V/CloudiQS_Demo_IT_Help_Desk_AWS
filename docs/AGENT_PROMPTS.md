# Agent prompts

Version: `helpdesk_supervisor_v1`  
Path: `services/agent_api/app/agent/prompts/helpdesk_supervisor_v1.md`

Copied from BUILD_WITH_CURSOR.md §7.1. Selected via `prompt_version` on `agent_runs`.

Simulator mode does not send this prompt to an LLM; it executes scripted tool workflows with the same tool ACL. Bedrock mode loads the prompt into Strands `system_prompt` and binds registry tools with server-injected `ActorContext`.
