$ErrorActionPreference = "Stop"
$body = '{"user_id":"NS-002"}'
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/auth/demo-login" -Method POST -Body $body -ContentType "application/json" -SessionVariable sess
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/dev/seed/reset" -Method POST -WebSession $sess -ContentType "application/json" -Body "{}"
Write-Host "Seed reset OK"
