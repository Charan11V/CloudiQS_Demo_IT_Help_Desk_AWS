import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import delete
from .db import SessionLocal, create_tables, drop_tables
from .models import *
from .config import get_settings

settings = get_settings()


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string"""
    if dt_str:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    return None


def load_seed_data():
    """Load seed data from demo_seed.json"""
    # Determine seed file path
    seed_path = os.path.join(settings.SPECS_PATH, "agentic_bakery_helpdesk", "demo_seed.json")
    
    # Fallback to local path if mounted path doesn't exist
    if not os.path.exists(seed_path):
        seed_path = "../../specs/agentic_bakery_helpdesk/demo_seed.json"
    
    if not os.path.exists(seed_path):
        print(f"⚠️  Warning: Seed file not found at {seed_path}")
        print("    Creating minimal seed data instead...")
        return create_minimal_seed()
    
    with open(seed_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def create_minimal_seed():
    """Create minimal seed data if demo_seed.json is not available"""
    return {
        "tenants": [
            {
                "tenant_id": "northstar",
                "display_name": "Northstar Technologies",
                "domain": "northstar.example",
                "config": {},
                "demo_mode": True
            }
        ],
        "users": [
            {
                "user_id": "NS-001",
                "tenant_id": "northstar",
                "display_name": "Asha Rao",
                "email": "ns001@northstar.example",
                "role": "employee",
                "department": "Engineering",
                "is_active": True,
                "version": 1
            },
            {
                "user_id": "NS-002",
                "tenant_id": "northstar",
                "display_name": "Rahul Sharma",
                "email": "ns002@northstar.example",
                "role": "it_engineer",
                "department": "IT Support",
                "is_active": True,
                "version": 1
            }
        ],
        "accounts": [],
        "devices": [],
        "vpn_profiles": [],
        "services": [],
        "applications": [],
        "app_installations": [],
        "entitlements": [],
        "mailboxes": [],
        "printers": [],
        "print_jobs": [],
        "security_events": [],
        "temporary_files": [],
        "tickets": []
    }


def seed_database(reset: bool = False):
    """Seed the database with demo data"""
    db = SessionLocal()
    
    try:
        if reset:
            print("🔄 Resetting database...")
            drop_tables()
            create_tables()
            print("✅ Database reset complete")
        
        # Check if already seeded
        existing_tenants = db.query(Tenant).count()
        if existing_tenants > 0 and not reset:
            print("ℹ️  Database already seeded. Use --reset to reset.")
            return
        
        print("📦 Loading seed data...")
        data = load_seed_data()
        
        # Seed tenants
        print("  → Seeding tenants...")
        for tenant_data in data.get("tenants", []):
            tenant = Tenant(
                tenant_id=tenant_data["tenant_id"],
                display_name=tenant_data["display_name"],
                domain=tenant_data["domain"],
                config=tenant_data.get("config") or tenant_data.get("policies") or {},
                demo_mode=tenant_data.get("demo_mode", tenant_data.get("simulation_mode", True)),
            )
            db.add(tenant)
        db.commit()
        
        # Seed users
        print("  → Seeding users...")
        for user_data in data.get("users", []):
            user = User(
                tenant_id=user_data["tenant_id"],
                user_id=user_data["user_id"],
                email=user_data["email"],
                display_name=user_data["display_name"],
                role=user_data["role"],
                department=user_data.get("department"),
                is_active=user_data.get("is_active", True),
                version=user_data.get("version", 1)
            )
            db.add(user)
        db.commit()
        
        # Seed accounts
        print("  → Seeding accounts...")
        for account_data in data.get("accounts", []):
            account = Account(
                account_id=account_data["account_id"],
                tenant_id=account_data["tenant_id"],
                user_id=account_data["user_id"],
                status=account_data.get("status", "active"),
                lock_reason=account_data.get("lock_reason"),
                failed_logins=account_data.get("failed_logins", 0),
                mfa_enabled=account_data.get("mfa_enabled", True),
                password_expired=account_data.get("password_expired", False),
                credentials_version=account_data.get("credentials_version", 1),
                risk_flag=account_data.get("risk_flag", False),
                version=account_data.get("version", 1)
            )
            db.add(account)
        db.commit()
        
        # Seed devices
        print("  → Seeding devices...")
        for device_data in data.get("devices", []):
            total = float(device_data.get("disk_total_gb", 256) or 256)
            free = float(device_data.get("disk_free_gb", 50) or 50)
            device = Device(
                device_id=device_data["device_id"],
                tenant_id=device_data["tenant_id"],
                assigned_to=device_data["assigned_to"],
                device_name=device_data.get("device_name")
                or device_data.get("hostname")
                or device_data.get("device_id"),
                platform=device_data.get("platform") or device_data.get("os") or device_data.get("type"),
                asset_tag=device_data.get("asset_tag"),
                disk_total_gb=int(total),
                disk_free_gb=int(free),
                disk_free_pct=round((free / total) * 100, 2) if total else 0,
                cpu_percent=device_data.get("cpu_percent", 30.0),
                memory_percent=device_data.get("memory_percent", 50.0),
                temperature_celsius=device_data.get("temperature_c") or device_data.get("temperature_celsius"),
                battery_health=device_data.get("battery_health", "good"),
                restart_pending=device_data.get("restart_pending", False),
                reboot_count=device_data.get("reboot_count", 0),
                wifi_enabled=device_data.get("wifi_enabled", True),
                dns_status=device_data.get("dns_status", "healthy"),
                health=device_data.get("health", "healthy"),
                last_heartbeat=parse_datetime(device_data.get("last_heartbeat")),
                version=device_data.get("version", 1)
            )
            db.add(device)
        db.commit()
        
        # Seed temporary files
        print("  → Seeding temporary files...")
        for file_data in data.get("temporary_files", []):
            size_gb = float(file_data.get("size_gb") or 0)
            size_bytes = int(file_data.get("size_bytes") or size_gb * (1024 ** 3))
            path_label = file_data.get("path_label") or file_data.get("file_path") or "temp"
            temp_file = TemporaryFile(
                object_id=file_data.get("object_id"),
                tenant_id=file_data["tenant_id"],
                device_id=file_data["device_id"],
                file_path=file_data.get("file_path") or path_label,
                path_label=path_label,
                size_bytes=size_bytes,
                size_gb=size_gb or (size_bytes / (1024 ** 3)),
                category=file_data.get("category"),
                removed=file_data.get("removed", False)
            )
            db.add(temp_file)
        db.commit()
        
        # Seed VPN profiles
        print("  → Seeding VPN profiles...")
        for vpn_data in data.get("vpn_profiles", []):
            vpn = VpnProfile(
                vpn_id=vpn_data["vpn_id"],
                tenant_id=vpn_data["tenant_id"],
                device_id=vpn_data["device_id"],
                user_id=vpn_data["user_id"],
                client_version=vpn_data.get("client_version"),
                min_client_version=vpn_data.get("min_client_version"),
                cert_expires_at=parse_datetime(vpn_data.get("cert_expires_at")),
                last_failure=vpn_data.get("last_failure"),
                connection_status=vpn_data.get("connection_status", "disconnected"),
                status=vpn_data.get("status", "active"),
                version=vpn_data.get("version", 1)
            )
            db.add(vpn)
        db.commit()
        
        # Seed services
        print("  → Seeding services...")
        for service_data in data.get("services", []):
            service = Service(
                service_id=service_data["service_id"],
                tenant_id=service_data["tenant_id"],
                service_name=service_data.get("service_name") or service_data["service_id"],
                status=service_data.get("status", "healthy"),
                active_incident_id=service_data.get("active_incident_id"),
                version=service_data.get("version", 1)
            )
            db.add(service)
        db.commit()
        
        # Seed applications
        print("  → Seeding applications...")
        for app_data in data.get("applications", []):
            app = Application(
                app_id=app_data["app_id"],
                tenant_id=app_data["tenant_id"],
                app_name=app_data.get("app_name") or app_data.get("name") or app_data["app_id"],
                approved_version=app_data.get("approved_version"),
                allowed_to_self_install=app_data.get("allowed_to_self_install", False),
                requires_licence=app_data.get("requires_licence", False)
            )
            db.add(app)
        db.commit()
        
        # Seed app installations
        print("  → Seeding app installations...")
        for install_data in data.get("app_installations", []):
            installation = AppInstallation(
                installation_id=install_data["installation_id"],
                tenant_id=install_data["tenant_id"],
                device_id=install_data["device_id"],
                user_id=install_data["user_id"],
                app_id=install_data["app_id"],
                installed_version=install_data.get("installed_version"),
                health=install_data.get("health", "healthy"),
                version=install_data.get("version", 1)
            )
            db.add(installation)
        db.commit()
        
        # Seed entitlements
        print("  → Seeding entitlements...")
        for ent_data in data.get("entitlements", []):
            entitlement = Entitlement(
                entitlement_id=ent_data["entitlement_id"],
                tenant_id=ent_data["tenant_id"],
                user_id=ent_data["user_id"],
                resource=ent_data["resource"],
                scope=ent_data["scope"],
                status=ent_data.get("status", "active"),
                version=ent_data.get("version", 1)
            )
            db.add(entitlement)
        db.commit()
        
        # Seed mailboxes
        print("  → Seeding mailboxes...")
        for mailbox_data in data.get("mailboxes", []):
            mailbox = Mailbox(
                mailbox_id=mailbox_data["mailbox_id"],
                tenant_id=mailbox_data["tenant_id"],
                user_id=mailbox_data["user_id"],
                used_gb=mailbox_data.get("used_gb", 0.0),
                quota_gb=mailbox_data.get("quota_gb", 50.0),
                archived_items=mailbox_data.get("archived_items", 0),
                sync_status=mailbox_data.get("sync_status", "healthy"),
                last_sync_at=parse_datetime(
                    mailbox_data.get("last_sync_at") or mailbox_data.get("sync_at")
                ),
                version=mailbox_data.get("version", 1)
            )
            db.add(mailbox)
        db.commit()
        
        # Seed printers
        print("  → Seeding printers...")
        for printer_data in data.get("printers", []):
            printer = Printer(
                printer_id=printer_data["printer_id"],
                tenant_id=printer_data["tenant_id"],
                printer_name=printer_data.get("printer_name")
                or printer_data.get("name")
                or printer_data["printer_id"],
                status=printer_data.get("status", "online"),
                version=printer_data.get("version", 1)
            )
            db.add(printer)
        db.commit()
        
        # Seed print jobs
        print("  → Seeding print jobs...")
        for job_data in data.get("print_jobs", []):
            print_job = PrintJob(
                job_id=job_data.get("job_id") or job_data.get("print_job_id"),
                tenant_id=job_data["tenant_id"],
                user_id=job_data["user_id"],
                printer_id=job_data["printer_id"],
                document_name=job_data.get("document_name"),
                status=job_data.get("status", "pending"),
                version=job_data.get("version", 1)
            )
            db.add(print_job)
        db.commit()
        
        # Seed security events
        print("  → Seeding security events...")
        for event_data in data.get("security_events", []):
            security_event = SecurityEvent(
                event_id=event_data["event_id"],
                tenant_id=event_data["tenant_id"],
                user_id=event_data.get("user_id"),
                severity=event_data.get("severity"),
                event_type=event_data.get("event_type") or event_data.get("type"),
                description=event_data.get("description"),
                review_status=event_data.get("review_status", "pending"),
                observed_at=parse_datetime(
                    event_data.get("observed_at") or event_data.get("occurred_at")
                ),
            )
            db.add(security_event)
        db.commit()
        
        # Seed tickets
        print("  → Seeding tickets...")
        for ticket_data in data.get("tickets", []):
            ticket = Ticket(
                ticket_id=ticket_data["ticket_id"],
                tenant_id=ticket_data["tenant_id"],
                requester=ticket_data.get("requester") or ticket_data.get("requester_id"),
                issue_code=ticket_data.get("issue_code"),
                summary=ticket_data.get("summary") or ticket_data.get("title") or "Ticket",
                description=ticket_data.get("description"),
                status=ticket_data.get("status", "open"),
                priority=ticket_data.get("priority", "medium"),
                assigned_team=ticket_data.get("assigned_team") or ticket_data.get("assigned_to"),
                version=ticket_data.get("version", 1)
            )
            db.add(ticket)
        db.commit()
        
        print("✅ Database seeded successfully!")
        
        # Print summary
        tenant_count = db.query(Tenant).count()
        user_count = db.query(User).count()
        account_count = db.query(Account).count()
        device_count = db.query(Device).count()
        
        print(f"\n📊 Summary:")
        print(f"   Tenants: {tenant_count}")
        print(f"   Users: {user_count}")
        print(f"   Accounts: {account_count}")
        print(f"   Devices: {device_count}")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    reset = "--reset" in sys.argv
    seed_database(reset=reset)
