#!/usr/bin/env python3
"""CloudiQS demo AWS operations helpers (SSM, inventory, cost snapshot, destroy guards)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

PROJECT = "CloudiQSDemo"
PREFIX = "cloudiqs-demo"
REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
PROFILE = os.environ.get("AWS_PROFILE", "cloudiqs-demo-deployer")


def session() -> boto3.Session:
    try:
        return boto3.Session(profile_name=PROFILE, region_name=REGION)
    except Exception:
        return boto3.Session(region_name=REGION)


def get_stack_outputs(cfn, stack="CloudiQSDemoStack") -> dict:
    try:
        stacks = cfn.describe_stacks(StackName=stack)["Stacks"]
        return {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}
    except ClientError as e:
        print(f"Stack outputs unavailable: {e}", file=sys.stderr)
        return {}


def cmd_status(_: argparse.Namespace) -> int:
    s = session()
    cfn = s.client("cloudformation")
    ec2 = s.client("ec2")
    outs = get_stack_outputs(cfn)
    print(json.dumps({"region": REGION, "profile": PROFILE, "outputs": outs}, indent=2))
    if outs.get("InstanceId"):
        desc = ec2.describe_instances(InstanceIds=[outs["InstanceId"]])
        inst = desc["Reservations"][0]["Instances"][0]
        print("InstanceState:", inst["State"]["Name"])
        print("InstanceType:", inst["InstanceType"])
    return 0


def cmd_cost_status(_: argparse.Namespace) -> int:
    s = session()
    ce = s.client("ce")
    budgets = s.client("budgets")
    sts = s.client("sts")
    acct = sts.get_caller_identity()["Account"]
    today = datetime.now(timezone.utc).date()
    start = today.replace(day=1).isoformat()
    end = today.isoformat()
    print("NOTE: Cost Explorer / Budgets data can lag 24–48h. Not real-time.")
    try:
        usage = ce.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        amt = usage["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"]
        print(f"MTD UnblendedCost (account): ${float(amt):.4f}")
    except ClientError as e:
        print("Cost Explorer unavailable:", e)

    try:
        b = budgets.describe_budget(AccountId=acct, BudgetName="CloudiQSDemo-Monthly")
        lim = b["Budget"]["BudgetLimit"]
        print(f"Budget: {b['Budget']['BudgetName']} limit={lim['Amount']} {lim['Unit']}")
    except ClientError as e:
        print("Budget lookup:", e)

    # Rough burn from running instance
    cfn = s.client("cloudformation")
    outs = get_stack_outputs(cfn)
    if outs.get("InstanceId"):
        ec2 = s.client("ec2")
        inst = ec2.describe_instances(InstanceIds=[outs["InstanceId"]])["Reservations"][0]["Instances"][0]
        state = inst["State"]["Name"]
        itype = inst["InstanceType"]
        rates = {"t4g.micro": 0.0084, "t4g.small": 0.0168, "t4g.medium": 0.0336}
        hourly = rates.get(itype, 0.02)
        print(f"Instance {outs['InstanceId']} state={state} type={itype}")
        if state == "running":
            print(f"Estimated compute burn ~${hourly:.4f}/hr (~${hourly*24:.2f}/day) + EBS/IPv4/CF")
        else:
            print("Compute burn ~$0/hr while stopped (EBS + public IPv4 + ECR/S3 still accrue)")
    return 0


def _find_instance(s) -> str | None:
    outs = get_stack_outputs(s.client("cloudformation"))
    return outs.get("InstanceId")


def cmd_ssm_run(args: argparse.Namespace) -> int:
    s = session()
    ssm = s.client("ssm")
    iid = args.instance_id or _find_instance(s)
    if not iid:
        print("No instance id", file=sys.stderr)
        return 1
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": args.commands},
        TimeoutSeconds=args.timeout,
    )
    cmd_id = resp["Command"]["CommandId"]
    print("CommandId:", cmd_id)
    for _ in range(60):
        time.sleep(3)
        inv = ssm.get_command_invocation(CommandId=cmd_id, InstanceId=iid)
        status = inv["Status"]
        if status in ("Success", "Cancelled", "TimedOut", "Failed"):
            print(status)
            print(inv.get("StandardOutputContent", ""))
            err = inv.get("StandardErrorContent", "")
            if err:
                print(err, file=sys.stderr)
            return 0 if status == "Success" else 1
    print("Timed out waiting for SSM", file=sys.stderr)
    return 1


def cmd_stop(_: argparse.Namespace) -> int:
    s = session()
    iid = _find_instance(s)
    if not iid:
        return 1
    s.client("ec2").stop_instances(InstanceIds=[iid])
    print(f"Stopping {iid}")
    return 0


def cmd_start(_: argparse.Namespace) -> int:
    s = session()
    iid = _find_instance(s)
    if not iid:
        return 1
    s.client("ec2").start_instances(InstanceIds=[iid])
    print(f"Starting {iid}")
    return 0


def cmd_inventory(_: argparse.Namespace) -> int:
    s = session()
    rg = s.client("resourcegroupstaggingapi")
    paginator = rg.get_paginator("get_resources")
    resources = []
    for page in paginator.paginate(TagFilters=[{"Key": "Project", "Values": [PROJECT]}]):
        for r in page.get("ResourceTagMappingList", []):
            resources.append({"arn": r["ResourceARN"], "tags": {t["Key"]: t["Value"] for t in r.get("Tags", [])}})
    print(json.dumps(resources, indent=2))
    print(f"Total tagged Project={PROJECT}: {len(resources)}")
    return 0


def cmd_destroy_guard(args: argparse.Namespace) -> int:
    if args.confirm != PROJECT:
        print(f"Refused. Pass --confirm {PROJECT}")
        return 2
    cmd_inventory(args)
    print("Inventory listed. Run: cd infra/cdk && npx cdk destroy --all --force")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="CloudiQS demo AWS ops")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("cost-status").set_defaults(func=cmd_cost_status)
    sub.add_parser("inventory").set_defaults(func=cmd_inventory)
    sub.add_parser("stop").set_defaults(func=cmd_stop)
    sub.add_parser("start").set_defaults(func=cmd_start)

    d = sub.add_parser("destroy-guard")
    d.add_argument("--confirm", required=True)
    d.set_defaults(func=cmd_destroy_guard)

    r = sub.add_parser("ssm-run")
    r.add_argument("--instance-id")
    r.add_argument("--timeout", type=int, default=600)
    r.add_argument("commands", nargs="+")
    r.set_defaults(func=cmd_ssm_run)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
