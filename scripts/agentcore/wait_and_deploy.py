#!/usr/bin/env python3
"""Poll AgentCore Total Agents quota / open case, then deploy when Value > 0."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from common import REGION, boto_session
from deploy_agent import main as deploy_main

QUOTA_CODE = "L-F4575653"
REQUEST_IDS = [
    "b694b29b7f9846559b0e9fb5ed590484LmNHtIAm",
]


def quota_value() -> float:
    sq = boto_session().client("service-quotas")
    q = sq.get_service_quota(ServiceCode="bedrock-agentcore", QuotaCode=QUOTA_CODE)
    return float(q["Quota"]["Value"])


def request_status() -> list[dict]:
    sq = boto_session().client("service-quotas")
    out = []
    for rid in REQUEST_IDS:
        try:
            out.append(sq.get_requested_service_quota_change(RequestId=rid)["RequestedQuota"])
        except Exception as exc:
            out.append({"Id": rid, "error": str(exc)})
    return out


def main() -> int:
    max_wait = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
    interval = 60
    deadline = time.time() + max_wait
    while time.time() < deadline:
        val = quota_value()
        statuses = request_status()
        print(f"quota Value={val} requests={statuses}")
        if val > 0:
            print("Quota available — deploying AgentCore Runtime")
            return deploy_main()
        time.sleep(interval)
    print(
        "Timed out waiting for AgentCore quota. "
        "Account ContactInformation is UNVERIFIED and applied Total Agents quota is 0. "
        "AWS Support case was opened via Service Quotas; retry: "
        "python scripts/agentcore/wait_and_deploy.py"
    )
    return 2


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
