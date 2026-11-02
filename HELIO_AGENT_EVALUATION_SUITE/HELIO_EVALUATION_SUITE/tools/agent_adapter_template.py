"""Implement the adapter against the HELIO backend under test.

Required sync API:
    invoke_case(case:dict, turn_index:int, user_text:str, session_id:str) -> dict

Your adapter must authenticate the actor using case['actor'], create/continue a
conversation, invoke the REAL agent, wait for completion, and gather persisted
server tool events / audit records. DO NOT read any private oracle files here.

DO NOT return made-up tool events or mark provider='bedrock' unless actually invoked.
"""
from typing import Any

def invoke_case(case:dict,turn_index:int,user_text:str,session_id:str)->dict[str,Any]:
    # Replace with your real application's endpoint and auth/session bridge.
    # Example output shape is in docs/RESPONSE_CONTRACT.md.
    raise NotImplementedError('Connect to HELIO app API. Never return fabricated responses or tool traces.')
