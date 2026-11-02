# Fast Bakery API integration suite (requires compose.bakery.yaml up)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
$env:BAKERY_API_URL = if ($env:BAKERY_API_URL) { $env:BAKERY_API_URL } else { "http://127.0.0.1:8002" }
python -m pytest tests/bakery -q --tb=short
exit $LASTEXITCODE
