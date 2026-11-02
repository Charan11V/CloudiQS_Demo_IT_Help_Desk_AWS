#!/usr/bin/env python3
"""Clamp enterprise ticket timestamps so none sit in the future.

Seed data was generated with a Python modulo bug (`-i % N` → future dates).
This rewrites tickets / itsm_tickets / CSV so created_at/updated_at are
on or before "now", with stable hash-derived past times per ticket_id.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "cloudiqs_enterprise_demo_pack" / "data"
NOW = datetime.now(timezone.utc)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def past_from_id(ticket_id: str) -> datetime:
    """Deterministic past timestamp from ticket id (1–60 days ago)."""
    h = int(hashlib.md5(ticket_id.encode("utf-8")).hexdigest()[:8], 16)
    days = 1 + (h % 60)
    hours = h % 24
    minutes = (h // 7) % 60
    return NOW - timedelta(days=days, hours=hours, minutes=minutes)


def normalize_pair(
    ticket_id: str, created_raw: str | None, updated_raw: str | None
) -> tuple[str, str]:
    created = parse_ts(created_raw)
    updated = parse_ts(updated_raw)

    if created is None or created > NOW:
        created = past_from_id(ticket_id)
    if updated is None or updated > NOW or updated < created:
        # Keep update shortly after create, still not in the future
        lag_hours = 1 + (int(hashlib.md5((ticket_id + ":u").encode()).hexdigest()[:4], 16) % 48)
        updated = min(NOW, created + timedelta(hours=lag_hours))
        if updated < created:
            updated = created

    return iso(created), iso(updated)


def fix_sqlite(path: Path) -> int:
    if not path.exists():
        print(f"skip missing {path}")
        return 0
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    changed = 0

    rows = conn.execute(
        "SELECT ticket_id, created_at, updated_at, attributes FROM tickets"
    ).fetchall()
    for row in rows:
        tid = row["ticket_id"]
        created, updated = normalize_pair(tid, row["created_at"], row["updated_at"])
        if created != row["created_at"] or updated != row["updated_at"]:
            attrs = row["attributes"]
            try:
                meta = json.loads(attrs) if attrs else {}
                if isinstance(meta, dict):
                    meta["created_at"] = created
                    meta["updated_at"] = updated
                    attrs = json.dumps(meta, ensure_ascii=False)
            except Exception:
                pass
            conn.execute(
                "UPDATE tickets SET created_at=?, updated_at=?, attributes=? WHERE ticket_id=?",
                (created, updated, attrs, tid),
            )
            changed += 1

    sr = conn.execute(
        "SELECT source_key, tenant_id, ordinal, json_record FROM source_records "
        "WHERE source_key='itsm_tickets'"
    ).fetchall()
    for row in sr:
        rec = json.loads(row["json_record"])
        tid = rec.get("ticket_id") or f"{row['tenant_id']}-{row['ordinal']}"
        created, updated = normalize_pair(tid, rec.get("created_at"), rec.get("updated_at"))
        resolved = parse_ts(rec.get("resolved_at"))
        if created != rec.get("created_at") or updated != rec.get("updated_at") or (
            resolved and resolved > NOW
        ):
            rec["created_at"] = created
            rec["updated_at"] = updated
            if resolved and resolved > NOW:
                rec["resolved_at"] = updated
            conn.execute(
                "UPDATE source_records SET json_record=? "
                "WHERE source_key=? AND tenant_id=? AND ordinal=?",
                (
                    json.dumps(rec, ensure_ascii=False, sort_keys=True),
                    row["source_key"],
                    row["tenant_id"],
                    row["ordinal"],
                ),
            )
            changed += 1

    conn.commit()
    conn.close()
    print(f"fixed {changed} rows in {path}")
    return changed


def fix_csv(path: Path) -> int:
    if not path.exists():
        print(f"skip missing {path}")
        return 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    changed = 0
    for row in rows:
        tid = row.get("ticket_id") or "unknown"
        created, updated = normalize_pair(tid, row.get("created_at"), row.get("updated_at"))
        if created != row.get("created_at") or updated != row.get("updated_at"):
            row["created_at"] = created
            row["updated_at"] = updated
            resolved = parse_ts(row.get("resolved_at"))
            if resolved and resolved > NOW:
                row["resolved_at"] = updated
            changed += 1

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"fixed {changed} rows in {path}")
    return changed


def main() -> None:
    print(f"NOW={iso(NOW)}")
    total = 0
    total += fix_sqlite(PACK / "runtime.sqlite")
    total += fix_sqlite(PACK / "canonical" / "enterprise.sqlite")
    total += fix_csv(PACK / "csv" / "tickets.csv")
    print(f"done, touched={total}")


if __name__ == "__main__":
    main()
