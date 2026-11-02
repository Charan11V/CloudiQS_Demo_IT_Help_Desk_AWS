# Full Bakery verification: seed reset + pytest + legacy P0 script
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
$env:BAKERY_API_URL = if ($env:BAKERY_API_URL) { $env:BAKERY_API_URL } else { "http://127.0.0.1:8002" }
python -m pytest tests/bakery -v --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/bakery_p0_retest.py
exit $LASTEXITCODE
