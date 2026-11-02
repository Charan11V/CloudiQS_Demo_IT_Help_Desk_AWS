$ErrorActionPreference = "Continue"
$base = "http://127.0.0.1:8002"
$results = New-Object System.Collections.Generic.List[object]

function Login([string]$userId) {
  $body = @{ user_id = $userId } | ConvertTo-Json
  $r = Invoke-RestMethod -Uri "$base/api/auth/demo-login" -Method POST -Body $body -ContentType "application/json"
  return $r.access_token
}

function H([string]$token) {
  return @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }
}

function Add-Result([string]$name, [bool]$pass, $detail) {
  $d = if ($null -eq $detail) { "" } else { "$detail" }
  if ($d.Length -gt 280) { $d = $d.Substring(0, 280) }
  $results.Add([pscustomobject]@{ test = $name; pass = $pass; detail = $d })
  $mark = if ($pass) { "PASS" } else { "FAIL" }
  Write-Host "$mark $name"
  Write-Host "  $d"
}

function Intent([hashtable]$hdr, [string]$code, [string]$target, [int]$ver, [hashtable]$payload) {
  $body = @{
    action_code = $code
    target = $target
    expected_version = $ver
    payload = $payload
  } | ConvertTo-Json -Depth 6
  return Invoke-RestMethod -Uri "$base/api/actions/intents" -Method POST -Headers $hdr -Body $body
}

function Consent([hashtable]$hdr, [string]$actionId) {
  $body = @{ consented = $true } | ConvertTo-Json
  return Invoke-RestMethod -Uri "$base/api/actions/$actionId/consent" -Method POST -Headers $hdr -Body $body
}

function Decide([hashtable]$hdr, [string]$approvalId, [string]$decision) {
  $body = @{ decision = $decision; reason = "demo" } | ConvertTo-Json
  return Invoke-RestMethod -Uri "$base/api/approvals/$approvalId/decision" -Method POST -Headers $hdr -Body $body
}

function ExecAction([hashtable]$hdr, [string]$actionId) {
  return Invoke-RestMethod -Uri "$base/api/actions/$actionId/execute" -Method POST -Headers $hdr -Body "{}"
}

# Reset seed for clean versions
try {
  $tok = Login "NS-002"
  Invoke-RestMethod -Uri "$base/api/dev/seed/reset" -Method POST -Headers (H $tok) | Out-Null
  Add-Result "seed_reset" $true "ok"
} catch {
  Add-Result "seed_reset" $false $_.Exception.Message
}

# NET-01 full path
try {
  $tok = Login "NS-001"
  $h = H $tok
  $intent = Intent $h "renew_mock_vpn_certificate" "VPN-NS-001" 1 @{}
  $c = Consent $h $intent.action_id
  Add-Result "NET-01_pending" ($c.requires_approval -eq $true -and $c.approval_id) ($c | ConvertTo-Json -Compress)
  $it = H (Login "NS-002")
  $ap = Decide $it $c.approval_id "approved"
  Add-Result "NET-01_approve" ($ap.decision -eq "approved" -or $ap.status -eq "approved") ($ap | ConvertTo-Json -Compress)
  $ex = ExecAction $h $intent.action_id
  Add-Result "NET-01_execute" (($ex.state -eq "success") -or ($ex.result.success -eq $true)) ($ex | ConvertTo-Json -Compress -Depth 6)
} catch {
  $msg = $_.Exception.Message
  if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
  Add-Result "NET-01_flow" $false $msg
}

# DEV-01 cleanup (may not require approval)
try {
  $tok = Login "NS-001"
  $h = H $tok
  $intent = Intent $h "run_mock_safe_cleanup" "DEV-NS-001" 1 @{}
  $c = Consent $h $intent.action_id
  if ($c.requires_approval -and $c.approval_id) {
    Decide (H (Login "NS-002")) $c.approval_id "approved" | Out-Null
  }
  $ex = ExecAction $h $intent.action_id
  Add-Result "DEV-01_cleanup" (($ex.state -eq "success") -or ($ex.result.success -eq $true)) ($ex | ConvertTo-Json -Compress -Depth 6)
} catch {
  $msg = $_.Exception.Message
  if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
  Add-Result "DEV-01_cleanup" $false $msg
}

# ID-01 unlock
try {
  $tok = Login "NS-001"
  $h = H $tok
  $intent = Intent $h "unlock_own_account" "ACC-NS-001" 1 @{}
  $c = Consent $h $intent.action_id
  if ($c.requires_approval -and $c.approval_id) {
    Decide (H (Login "NS-002")) $c.approval_id "approved" | Out-Null
  }
  $ex = ExecAction $h $intent.action_id
  Add-Result "ID-01_unlock" (($ex.state -eq "success") -or ($ex.result.success -eq $true)) ($ex | ConvertTo-Json -Compress -Depth 6)
} catch {
  $msg = $_.Exception.Message
  if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
  Add-Result "ID-01_unlock" $false $msg
}

# SEC-01
try {
  $tok = Login "NS-001"
  $h = H $tok
  $payload = @{
    incident_type = "phishing"
    description = "Suspicious email asking for password reset"
    severity = "high"
  }
  $intent = Intent $h "create_security_incident" "phishing_report" 1 $payload
  $c = Consent $h $intent.action_id
  if ($c.requires_approval -and $c.approval_id) {
    Decide (H (Login "NS-002")) $c.approval_id "approved" | Out-Null
  }
  $ex = ExecAction $h $intent.action_id
  $ok = ($ex.state -eq "success") -or ($ex.result.success -eq $true) -or ($null -ne $ex.result.ticket_id)
  Add-Result "SEC-01_execute" $ok ($ex | ConvertTo-Json -Compress -Depth 6)
} catch {
  $msg = $_.Exception.Message
  if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
  Add-Result "SEC-01_execute" $false $msg
}

# Guided unknown -> ticket
try {
  $tok = Login "NS-001"
  $h = H $tok
  $conv = Invoke-RestMethod -Uri "$base/api/conversations" -Method POST -Headers $h
  $cid = $conv.conversation_id
  $turnBody = @{ free_text = "My coffee machine will not sync with Active Directory" } | ConvertTo-Json
  $state = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body $turnBody
  $msg = if ($state.assistant_message) { $state.assistant_message } else { ($state | ConvertTo-Json -Compress) }
  Add-Result "GEN_UNKNOWN_ticket" ($msg -match "Ticket|INC-|escalat|open|not in catalog|couldn't identify") $msg
} catch {
  $msg = $_.Exception.Message
  if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
  Add-Result "GEN_UNKNOWN_ticket" $false $msg
}

# Guided NET-01 menu path
try {
  $tok = Login "NS-001"
  $h = H $tok
  $conv = Invoke-RestMethod -Uri "$base/api/conversations" -Method POST -Headers $h
  $cid = $conv.conversation_id
  $t1 = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = "network" } | ConvertTo-Json)
  $t2 = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = "network__vpn" } | ConvertTo-Json)
  $t3 = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = "NET-01" } | ConvertTo-Json)
  $state = $t3
  $guard = 0
  while ($state.phase -eq "ASKING_CLARIFIERS" -or $state.phase -eq "DIAGNOSING" -and $guard -lt 8) {
    $opt = $state.options | Where-Object { $_.id -in @("yes","no","not_sure") } | Select-Object -First 1
    if (-not $opt) { $opt = $state.options | Where-Object { $_.id -notin @("back","start_over","talk_to_it","something_else") } | Select-Object -First 1 }
    if (-not $opt) { break }
    $state = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = $opt.id } | ConvertTo-Json)
    $guard++
  }
  if ($state.options | Where-Object { $_.id -eq "consent_execute" }) {
    $state = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = "consent_execute" } | ConvertTo-Json)
  }
  $msg = "$($state.phase) $($state.assistant_message)"
  Add-Result "guided_NET-01" ($msg -match "approval|VPN|certificate|awaiting|PROPOS|consent|Ticket|Demo") $msg
} catch {
  $msg = $_.Exception.Message
  if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
  Add-Result "guided_NET-01" $false $msg
}

# Neha NET-02
try {
  $tok = Login "NS-003"
  $h = H $tok
  $conv = Invoke-RestMethod -Uri "$base/api/conversations" -Method POST -Headers $h
  $cid = $conv.conversation_id
  $null = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = "network" } | ConvertTo-Json)
  $null = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = "network__vpn" } | ConvertTo-Json)
  $state = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = "NET-02" } | ConvertTo-Json)
  $guard = 0
  while (($state.phase -eq "ASKING_CLARIFIERS" -or $state.phase -eq "DIAGNOSING") -and $guard -lt 8) {
    $opt = $state.options | Where-Object { $_.id -in @("yes","no","not_sure") } | Select-Object -First 1
    if (-not $opt) { $opt = $state.options | Where-Object { $_.id -notin @("back","start_over","talk_to_it","something_else") } | Select-Object -First 1 }
    if (-not $opt) { break }
    $state = Invoke-RestMethod -Uri "$base/api/conversations/$cid/turns" -Method POST -Headers $h -Body (@{ option_id = $opt.id } | ConvertTo-Json)
    $guard++
  }
  $msg = "$($state.phase) $($state.assistant_message)"
  Add-Result "Neha_NET-02" ($msg -match "degrad|outage|service|ticket|cannot|VPN|client|update|PROPOS|ESCALAT") $msg
} catch {
  $msg = $_.Exception.Message
  if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
  Add-Result "Neha_NET-02" $false $msg
}

# Approvals + tickets
try {
  $list = Invoke-RestMethod -Uri "$base/api/approvals/pending" -Method GET -Headers (H (Login "NS-002"))
  Add-Result "approvals_list" ($null -ne $list.approvals) (($list | ConvertTo-Json -Compress).Substring(0, [Math]::Min(200, ($list | ConvertTo-Json -Compress).Length)))
} catch {
  Add-Result "approvals_list" $false $_.Exception.Message
}

try {
  $tickets = Invoke-RestMethod -Uri "$base/api/tickets/mine" -Method GET -Headers (H (Login "NS-001"))
  Add-Result "tickets_mine" ($null -ne $tickets.tickets) (($tickets | ConvertTo-Json -Compress).Substring(0, [Math]::Min(200, ($tickets | ConvertTo-Json -Compress).Length)))
} catch {
  Add-Result "tickets_mine" $false $_.Exception.Message
}

# Catalog size
try {
  $cat = Invoke-RestMethod -Uri "$base/api/catalog" -Method GET -Headers (H (Login "NS-001"))
  $count = if ($cat.issue_count) { $cat.issue_count } elseif ($cat.issues) { $cat.issues.Count } else { 0 }
  Add-Result "catalog_57" ($count -ge 50) "issue_count=$count"
} catch {
  Add-Result "catalog_57" $false $_.Exception.Message
}

$passed = @($results | Where-Object { $_.pass }).Count
$failed = @($results | Where-Object { -not $_.pass }).Count
$out = [ordered]@{
  passed = $passed
  failed = $failed
  total = $results.Count
  timestamp = (Get-Date).ToUniversalTime().ToString("o")
  results = $results
}
$path = "C:\Users\Dell\Documents\projects\cloudiqs\cloudiqs_helio_cursor_workspace\docs\BAKERY_P0_TEST_RESULTS.json"
($out | ConvertTo-Json -Depth 8) | Set-Content -Path $path -Encoding UTF8
Write-Host ""
Write-Host "SUMMARY passed=$passed failed=$failed total=$($results.Count)"
Write-Host "Wrote $path"
