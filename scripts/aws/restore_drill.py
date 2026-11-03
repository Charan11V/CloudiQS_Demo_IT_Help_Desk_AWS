#!/usr/bin/env python3
"""Backup → restore drill for demo SQLite artifacts (evidence for recovery scorecard).

1) Copies current runtime.sqlite + app.sqlite to S3 under drills/
2) Downloads them back to a temp path on the instance and checksum-compares

Does not overwrite live DB unless --apply is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[2]


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
    ap.add_argument("--apply", action="store_true", help="Overwrite live sqlite from drill copy (destructive)")
    args = ap.parse_args()

    s = session()
    cfn = s.client("cloudformation")
    ssm = s.client("ssm")
    outs = {
        o["OutputKey"]: o["OutputValue"]
        for o in cfn.describe_stacks(StackName="CloudiQSDemoStack")["Stacks"][0]["Outputs"]
    }
    iid = outs["InstanceId"]
    bucket = outs["BackupBucketName"]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    apply = "1" if args.apply else "0"
    script = f"""
set -euo pipefail
BUCKET={bucket}
STAMP={stamp}
APPLY={apply}
mkdir -p /tmp/cloudiqs-drill
sha256sum /opt/cloudiqs-demo/data/runtime.sqlite /opt/cloudiqs-demo/data/app.sqlite > /tmp/cloudiqs-drill/before.sha256 || true
aws s3 cp /opt/cloudiqs-demo/data/runtime.sqlite s3://$BUCKET/drills/$STAMP/runtime.sqlite
aws s3 cp /opt/cloudiqs-demo/data/app.sqlite s3://$BUCKET/drills/$STAMP/app.sqlite
aws s3 cp s3://$BUCKET/drills/$STAMP/runtime.sqlite /tmp/cloudiqs-drill/runtime.sqlite
aws s3 cp s3://$BUCKET/drills/$STAMP/app.sqlite /tmp/cloudiqs-drill/app.sqlite
sha256sum /tmp/cloudiqs-drill/runtime.sqlite /tmp/cloudiqs-drill/app.sqlite > /tmp/cloudiqs-drill/after.sha256
# Compare basenames content hashes
python3 - <<'PY'
from pathlib import Path
b=Path('/tmp/cloudiqs-drill/before.sha256').read_text().splitlines()
a=Path('/tmp/cloudiqs-drill/after.sha256').read_text().splitlines()
bh={{line.split()[1].split('/')[-1]: line.split()[0] for line in b if line.strip()}}
ah={{line.split()[1].split('/')[-1]: line.split()[0] for line in a if line.strip()}}
ok = bh.get('runtime.sqlite')==ah.get('runtime.sqlite') and bh.get('app.sqlite')==ah.get('app.sqlite')
print('DRILL_CHECKSUM_OK' if ok else 'DRILL_CHECKSUM_FAIL', bh, ah)
raise SystemExit(0 if ok else 1)
PY
if [ "$APPLY" = "1" ]; then
  cp /tmp/cloudiqs-drill/runtime.sqlite /opt/cloudiqs-demo/data/runtime.sqlite
  cp /tmp/cloudiqs-drill/app.sqlite /opt/cloudiqs-demo/data/app.sqlite
  echo APPLIED_LIVE
fi
echo DRILL_OK s3://$BUCKET/drills/$STAMP/
"""
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [script]},
        TimeoutSeconds=600,
    )
    cmd = resp["Command"]["CommandId"]
    print("CommandId", cmd)
    for _ in range(60):
        time.sleep(5)
        inv = ssm.get_command_invocation(CommandId=cmd, InstanceId=iid)
        if inv["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
            print(inv.get("StandardOutputContent", ""))
            print(inv.get("StandardErrorContent", ""), file=sys.stderr)
            out = {
                "status": inv["Status"],
                "bucket_prefix": f"s3://{bucket}/drills/{stamp}/",
                "apply": bool(args.apply),
            }
            (ROOT / "docs" / "RESTORE_DRILL.json").write_text(
                json.dumps(out, indent=2), encoding="utf-8"
            )
            return 0 if inv["Status"] == "Success" else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
