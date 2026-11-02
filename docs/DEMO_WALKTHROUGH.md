# 4-minute demo walkthrough

1. `docker compose up --build -d` → open http://localhost:3000  
2. **Login as Asha Patel** (Northstar employee). Note Offline Simulator badge and synthetic timeline 31 Oct 2026.  
3. Open **AI Support**, ask: *My VPN won't connect and my laptop is very slow.*  
4. Inspect tool activity: identity → devices → diagnostics → VPN → KB → outages. Confirm findings: expired cert, high CPU / low disk, MDM noncompliance.  
5. Create ticket from suggested step (or My Tickets). Show ticket appears in list.  
6. Propose account unlock → switch persona to **Rahul** → Approvals → Approve + Execute → IdP becomes active.  
7. Switch to **Beacon / Neha**, propose unlock → **David** cannot approve unlock; **Noah** (security) can.  
8. As Asha, open a Beacon ticket URL/API → 404.  
9. Optional: Admin Vikram disables VPN integration; VPN tools fail safely. Evaluations page runs deterministic suite.

Do not claim Bedrock or AgentCore unless `MODEL_PROVIDER=bedrock` smoke succeeds.
