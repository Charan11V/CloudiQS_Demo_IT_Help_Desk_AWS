#!/usr/bin/env python3
"""Human-approved scale signal for the cost-capped demo.

This does NOT silently spend money. It:
  1) Publishes / records an APPROVED_SCALE event (SSM param + optional SNS)
  2) Tags the EC2 instance ScaleApproved=true / ScaleTier=N
  3) Prints the next manual steps to actually add capacity (ECS/ASG) when you graduate off Compose

Default demo remains 1× t4g.small. Approval is the control plane proof for interviews.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import boto3


def session():
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return boto3.Session(region_name=os.environ.get("AWS_REGION", "us-east-1"))
    try:
        return boto3.Session(
            profile_name=os.environ.get("AWS_PROFILE", "cloudiqs-demo-deployer"),
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
    except Exception:
        return boto3.Session(region_name=os.environ.get("AWS_REGION", "us-east-1"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", type=int, default=2, help="Approved scale tier (2=dual, 3=small fleet)")
    ap.add_argument("--confirm", required=True, help="Must equal APPROVE_SCALE")
    args = ap.parse_args()
    if args.confirm != "APPROVE_SCALE":
        print("Refused: pass --confirm APPROVE_SCALE")
        return 2

    s = session()
    cfn = s.client("cloudformation")
    ec2 = s.client("ec2")
    ssm = s.client("ssm")
    outs = {
        o["OutputKey"]: o["OutputValue"]
        for o in cfn.describe_stacks(StackName="CloudiQSDemoStack")["Stacks"][0]["Outputs"]
    }
    iid = outs["InstanceId"]
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = {
        "approved_at": stamp,
        "tier": args.tier,
        "instance_id": iid,
        "note": "Human approved scale intent. Compose demo stays single-node until ECS/ASG cutover.",
    }
    ssm.put_parameter(
        Name="/cloudiqs-demo/SCALE_APPROVAL",
        Value=json.dumps(payload),
        Type="String",
        Overwrite=True,
    )
    ec2.create_tags(
        Resources=[iid],
        Tags=[
            {"Key": "ScaleApproved", "Value": "true"},
            {"Key": "ScaleTier", "Value": str(args.tier)},
            {"Key": "ScaleApprovedAt", "Value": stamp},
        ],
    )
    print(json.dumps(payload, indent=2))
    print(
        "Recorded approval. No extra compute was started. "
        "To spend money you must deliberately provision ASG/ECS (see docs/SCALE_APPROVAL.md)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
