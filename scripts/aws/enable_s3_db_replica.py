#!/usr/bin/env python3
"""Replicate the live demo databases to the existing S3 backup bucket.

SQLite stays on local disk so reads and writes stay fast. Litestream copies the
WAL to s3://<backup-bucket>/db-replica/ every few seconds. Postgres is dumped
every five minutes to the same prefix. Existing files are moved, never deleted.
A missing local file is restored from S3 before Litestream starts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "aws"))

from fast_deploy import env_export_snippet, session, stack_outputs, wait_cmd  # noqa: E402

REMOTE = r"""
set -euo pipefail
echo "CHECKPOINT"
if docker ps --format '{{.Names}}' | grep -q enterprise-mock-api; then
  docker exec "$(docker ps -qf name=enterprise-mock-api | head -n 1)" python -c 'import sqlite3; c=sqlite3.connect("/app/data/runtime.sqlite"); c.execute("PRAGMA wal_checkpoint(TRUNCATE)"); print("mock", c.execute("PRAGMA journal_mode").fetchone())'
fi
if docker ps --format '{{.Names}}' | grep -q agent-api; then
  docker exec "$(docker ps -qf name=agent-api | head -n 1)" python -c 'import sqlite3; c=sqlite3.connect("/data/app.sqlite"); c.execute("PRAGMA wal_checkpoint(TRUNCATE)"); print("agent", c.execute("PRAGMA journal_mode").fetchone())'
fi

echo "STOP_DB_CONTAINERS"
docker stop compose-agent-api-1 compose-enterprise-mock-api-1 || true

mkdir -p /opt/cloudiqs-demo/data/mock /opt/cloudiqs-demo/data/agent /opt/cloudiqs-demo/bin
move_db() {
  src="$1"; dest="$2"
  if [ -f "$src" ] && [ ! -e "$dest" ]; then
    mv "$src" "$dest"
  elif [ -f "$src" ] && [ -f "$dest" ]; then
    src_sz=$(stat -c%s "$src")
    dest_sz=$(stat -c%s "$dest")
    if [ "$src_sz" -gt "$dest_sz" ]; then
      mv "$dest" "${dest}.smaller-bak"
      mv "$src" "$dest"
    fi
  fi
  test -s "$dest"
  echo "DB $dest $(stat -c%s "$dest") bytes"
}
move_db /opt/cloudiqs-demo/data/runtime.sqlite /opt/cloudiqs-demo/data/mock/runtime.sqlite
move_db /opt/cloudiqs-demo/data/app.sqlite /opt/cloudiqs-demo/data/agent/app.sqlite
for ext in -wal -shm; do
  if [ -f "/opt/cloudiqs-demo/data/runtime.sqlite${ext}" ]; then
    mv "/opt/cloudiqs-demo/data/runtime.sqlite${ext}" "/opt/cloudiqs-demo/data/mock/runtime.sqlite${ext}" || true
  fi
  if [ -f "/opt/cloudiqs-demo/data/app.sqlite${ext}" ]; then
    mv "/opt/cloudiqs-demo/data/app.sqlite${ext}" "/opt/cloudiqs-demo/data/agent/app.sqlite${ext}" || true
  fi
done

python3 - <<'PY'
import os, sqlite3
for p in ("/opt/cloudiqs-demo/data/mock/runtime.sqlite", "/opt/cloudiqs-demo/data/agent/app.sqlite"):
    c = sqlite3.connect(p)
    mode = c.execute("PRAGMA journal_mode=WAL").fetchone()
    c.commit()
    c.close()
    print("WAL", p, mode, os.path.getsize(p))
PY

if ! command -v litestream >/dev/null 2>&1; then
  arch=$(uname -m)
  case "$arch" in
    aarch64|arm64) lsarch=arm64 ;;
    x86_64) lsarch=amd64 ;;
    *) echo "unsupported arch $arch"; exit 1 ;;
  esac
  curl -fsSL -o /tmp/litestream.tar.gz "https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-${lsarch}.tar.gz"
  tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz
  chmod 755 /usr/local/bin/litestream
fi
litestream version

set +e
source /opt/cloudiqs-demo/env.sh
set -e
test -n "${BACKUP_BUCKET:-}"
cat > /etc/litestream.yml <<EOF
dbs:
  - path: /opt/cloudiqs-demo/data/mock/runtime.sqlite
    replicas:
      - url: s3://${BACKUP_BUCKET}/db-replica/mock
        region: us-east-1
        retention: 72h
        sync-interval: 10s
  - path: /opt/cloudiqs-demo/data/agent/app.sqlite
    replicas:
      - url: s3://${BACKUP_BUCKET}/db-replica/agent
        region: us-east-1
        retention: 72h
        sync-interval: 10s
EOF
chmod 640 /etc/litestream.yml

cat > /opt/cloudiqs-demo/bin/restore-sqlite-if-missing.sh <<EOF
#!/bin/bash
set -euo pipefail
restore_one() {
  dest="\$1"
  url="\$2"
  if [ -s "\$dest" ]; then
    return 0
  fi
  mkdir -p "\$(dirname "\$dest")"
  if litestream restore -h 2>&1 | grep -q if-replica-exists; then
    litestream restore -if-replica-exists -o "\$dest" "\$url" || true
  else
    litestream restore -o "\$dest" "\$url" || true
  fi
}
restore_one /opt/cloudiqs-demo/data/mock/runtime.sqlite s3://${BACKUP_BUCKET}/db-replica/mock
restore_one /opt/cloudiqs-demo/data/agent/app.sqlite s3://${BACKUP_BUCKET}/db-replica/agent
EOF
chmod 755 /opt/cloudiqs-demo/bin/restore-sqlite-if-missing.sh

cat > /etc/systemd/system/litestream.service <<'EOF'
[Unit]
Description=Replicate HELIO SQLite databases to S3
After=network-online.target
Wants=network-online.target
[Service]
Environment=AWS_REGION=us-east-1
Environment=AWS_DEFAULT_REGION=us-east-1
ExecStartPre=/opt/cloudiqs-demo/bin/restore-sqlite-if-missing.sh
ExecStart=/usr/local/bin/litestream replicate -config /etc/litestream.yml
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

cat > /opt/cloudiqs-demo/bin/backup-bakery.sh <<EOF
#!/bin/bash
set -euo pipefail
source /opt/cloudiqs-demo/env.sh
cid=\$(docker ps -qf name=bakery-postgres | head -n 1)
if [ -z "\$cid" ]; then
  echo "bakery postgres not running" >&2
  exit 0
fi
stamp=\$(date -u +%Y%m%dT%H%M%SZ)
tmp=\$(mktemp)
docker exec "\$cid" pg_dump -U bakery --format=custom bakery > "\$tmp"
aws s3 cp "\$tmp" "s3://${BACKUP_BUCKET}/db-replica/bakery/latest.dump" --only-show-errors
aws s3 cp "\$tmp" "s3://${BACKUP_BUCKET}/db-replica/bakery/bakery-\${stamp}.dump" --only-show-errors
rm -f "\$tmp"
echo "bakery dump \$stamp"
EOF
chmod 755 /opt/cloudiqs-demo/bin/backup-bakery.sh

cat > /etc/systemd/system/bakery-s3-backup.service <<'EOF'
[Unit]
Description=Dump bakery Postgres to S3
[Service]
Type=oneshot
ExecStart=/opt/cloudiqs-demo/bin/backup-bakery.sh
EOF
cat > /etc/systemd/system/bakery-s3-backup.timer <<'EOF'
[Unit]
Description=Dump bakery Postgres to S3 every 5 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable litestream.service bakery-s3-backup.timer
systemctl restart litestream.service
systemctl start bakery-s3-backup.timer
systemctl start bakery-s3-backup.service

aws s3 cp "s3://${BACKUP_BUCKET}/deploy/compose.aws.yaml" /opt/cloudiqs-demo/compose/compose.aws.yaml
cd /opt/cloudiqs-demo/compose
docker compose -f compose.aws.yaml up -d --no-deps --force-recreate enterprise-mock-api
docker compose -f compose.aws.yaml up -d --no-deps --force-recreate agent-api
ok=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if docker exec "$(docker ps -qf name=enterprise-mock-api | head -n 1)" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health")' \
    && docker exec "$(docker ps -qf name=agent-api | head -n 1)" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8001/health")'; then
    ok=1
    break
  fi
  sleep 3
done
test "$ok" = 1
echo HEALTH_OK
echo "LITESTREAM $(systemctl is-active litestream)"
sleep 12
aws s3 ls "s3://${BACKUP_BUCKET}/db-replica/" --recursive
echo S3_DB_REPLICA_OK
"""


def status() -> int:
    s = session()
    outs = stack_outputs(s.client("cloudformation"))
    bucket = outs["BackupBucketName"]
    iid = outs["InstanceId"]
    script = f"""
set +e
echo MOCK $(docker exec "$(docker ps -qf name=enterprise-mock-api | head -n 1)" python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health").read().decode())')
echo AGENT $(docker exec "$(docker ps -qf name=agent-api | head -n 1)" python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8001/health").read().decode())')
echo LITESTREAM $(systemctl is-active litestream || true)
systemctl is-active bakery-s3-backup.timer || true
journalctl -u litestream -n 30 --no-pager || true
systemctl start bakery-s3-backup.service || true
aws s3 ls s3://{bucket}/db-replica/ --recursive
echo STATUS_DONE
"""
    ssm = s.client("ssm")
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [script]},
        TimeoutSeconds=180,
    )
    print("SSM", resp["Command"]["CommandId"])
    return wait_cmd(ssm, resp["Command"]["CommandId"], iid, timeout_s=180)


def repair() -> int:
    """Point the mock API at the moved database and set the S3 region."""
    s = session()
    cfn = s.client("cloudformation")
    s3c = s.client("s3")
    ssm = s.client("ssm")
    outs = stack_outputs(cfn)
    bucket = outs["BackupBucketName"]
    iid = outs["InstanceId"]
    s3c.put_object(
        Bucket=bucket,
        Key="deploy/compose.aws.yaml",
        Body=(ROOT / "compose.aws.yaml").read_bytes(),
    )
    remote = f"""
set -euo pipefail
source /opt/cloudiqs-demo/env.sh
cat > /etc/litestream.yml <<EOF
dbs:
  - path: /opt/cloudiqs-demo/data/mock/runtime.sqlite
    replicas:
      - url: s3://{bucket}/db-replica/mock
        region: us-east-1
        retention: 72h
        sync-interval: 10s
  - path: /opt/cloudiqs-demo/data/agent/app.sqlite
    replicas:
      - url: s3://{bucket}/db-replica/agent
        region: us-east-1
        retention: 72h
        sync-interval: 10s
EOF
chmod 640 /etc/litestream.yml
systemctl restart litestream
aws s3 cp s3://{bucket}/deploy/compose.aws.yaml /opt/cloudiqs-demo/compose/compose.aws.yaml
cd /opt/cloudiqs-demo/compose
docker compose -f compose.aws.yaml up -d --no-deps --force-recreate enterprise-mock-api
ok=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if docker exec "$(docker ps -qf name=enterprise-mock-api | head -n 1)" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health")'; then
    ok=1
    break
  fi
  sleep 3
done
test "$ok" = 1
echo MOCK_HEALTH_OK
sleep 15
journalctl -u litestream -n 15 --no-pager
aws s3 ls s3://{bucket}/db-replica/ --recursive
echo REPAIR_OK
"""
    script = "\n".join(env_export_snippet() + [remote])
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [script]},
        TimeoutSeconds=300,
    )
    print("SSM", resp["Command"]["CommandId"])
    return wait_cmd(ssm, resp["Command"]["CommandId"], iid, timeout_s=300)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        return status()
    if len(sys.argv) > 1 and sys.argv[1] == "--repair":
        return repair()
    s = session()
    cfn = s.client("cloudformation")
    s3 = s.client("s3")
    ssm = s.client("ssm")
    outs = stack_outputs(cfn)
    bucket = outs["BackupBucketName"]
    iid = outs["InstanceId"]
    s3.put_object(
        Bucket=bucket,
        Key="deploy/compose.aws.yaml",
        Body=(ROOT / "compose.aws.yaml").read_bytes(),
    )
    script = "\n".join(env_export_snippet() + [REMOTE])
    print(f"[s3-db] SSM on {iid} bucket {bucket}")
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [script]},
        TimeoutSeconds=900,
    )
    cmd = resp["Command"]["CommandId"]
    print("SSM", cmd)
    return wait_cmd(ssm, cmd, iid, timeout_s=900)


if __name__ == "__main__":
    raise SystemExit(main())
