# Build linux/arm64 images locally and push to ECR.
# Requires: docker buildx, AWS auth (profile cloudiqs-demo-deployer preferred)
param(
  [string]$Profile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { "cloudiqs-demo-deployer" }),
  [string]$Region = "us-east-1",
  [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"
$env:Path = "C:\Program Files\Amazon\AWSCLIV2;$env:USERPROFILE\.local\bin;$env:Path"

$Account = (aws sts get-caller-identity --profile $Profile --query Account --output text)
$Registry = "$Account.dkr.ecr.$Region.amazonaws.com"

Write-Host "Account=$Account Region=$Region Tag=$Tag"

aws ecr get-login-password --region $Region --profile $Profile |
  docker login --username AWS --password-stdin $Registry

$repos = @(
  @{ Name = "cloudiqs-demo-web"; Context = "apps/web"; Dockerfile = "apps/web/Dockerfile"; BuildArgs = @("--build-arg","AGENT_API_URL=http://agent-api:8001") },
  @{ Name = "cloudiqs-demo-agent-api"; Context = "services/agent_api"; Dockerfile = "services/agent_api/Dockerfile"; BuildArgs = @() },
  @{ Name = "cloudiqs-demo-mock-api"; Context = "cloudiqs_enterprise_demo_pack"; Dockerfile = "cloudiqs_enterprise_demo_pack/Dockerfile"; BuildArgs = @() }
)

docker buildx create --name cloudiqsbuilder --use 2>$null | Out-Null
docker buildx inspect --bootstrap | Out-Null

foreach ($r in $repos) {
  $uri = "$Registry/$($r.Name):$Tag"
  Write-Host "Building $($r.Name) -> $uri"
  $args = @(
    "buildx","build","--platform","linux/arm64",
    "-f", $r.Dockerfile,
    "-t", $uri,
    "--push"
  ) + $r.BuildArgs + @($r.Context)
  & docker @args
  if ($LASTEXITCODE -ne 0) { throw "Build failed for $($r.Name)" }
}

Write-Host "All images pushed."
Write-Host "WEB=$Registry/cloudiqs-demo-web:$Tag"
Write-Host "AGENT=$Registry/cloudiqs-demo-agent-api:$Tag"
Write-Host "MOCK=$Registry/cloudiqs-demo-mock-api:$Tag"
