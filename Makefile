.PHONY: up down reset-demo logs smoke-bedrock eval test-mock test-agent \
	aws-status aws-logs aws-health aws-deploy aws-restart aws-backup-demo aws-restore-demo \
	aws-reset-demo aws-stop-demo aws-start-demo aws-cost-status aws-destroy-demo aws-inventory \
	aws-push-images aws-bootstrap aws-fast aws-fast-web aws-fast-agent aws-fast-bakery aws-fast-all \
	dev deploy-agent deploy-web deploy-all agentcore-status agentcore-logs agentcore-rollback destroy-agentcore

AWS_PROFILE ?= cloudiqs-demo-deployer
AWS_REGION ?= us-east-1
export AWS_PROFILE AWS_REGION

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

reset-demo:
	@echo "This will erase runtime demo mutations. Set CONFIRM=YES to proceed."
	@test "$(CONFIRM)" = "YES" || (echo "Refused: pass CONFIRM=YES"; exit 1)
	docker compose stop agent-api enterprise-mock-api
	docker compose run --rm --entrypoint sh enterprise-mock-api -c "cp /seed/enterprise.sqlite /app/data/runtime.sqlite || cp /app/data/canonical/enterprise.sqlite /app/data/runtime.sqlite"
	docker compose run --rm --entrypoint sh agent-api -c "rm -f /data/app.sqlite /data/app.sqlite-wal /data/app.sqlite-shm"
	docker compose up -d

test-mock:
	docker compose exec enterprise-mock-api pytest -q /app/tests || docker compose run --rm --entrypoint pytest enterprise-mock-api -q tests

test-agent:
	docker compose exec agent-api pytest -q

eval:
	docker compose exec agent-api python -c "print('Use UI /evaluations or POST /evaluations/runs')"

smoke-bedrock:
	@echo "Requires temporary AWS auth (aws login / instance role). No permanent keys."
	MODEL_PROVIDER=bedrock docker compose up -d agent-api
	docker compose exec agent-api python -c "from app.agent.factory import get_provider_info; print(get_provider_info())"

# ---- AWS ops ----
aws-bootstrap:
	python infra/bootstrap/create_deploy_role.py

aws-status:
	python scripts/aws/ops.py status

aws-cost-status:
	python scripts/aws/ops.py cost-status

aws-inventory:
	python scripts/aws/ops.py inventory

aws-stop-demo:
	python scripts/aws/ops.py stop

aws-start-demo:
	python scripts/aws/ops.py start

aws-push-images:
	pwsh -File scripts/aws/push_images.ps1 -Profile $(AWS_PROFILE) -Region $(AWS_REGION)

# Fast path: native ARM build on the existing demo EC2 (no QEMU). Same cost.
aws-fast:
	python scripts/aws/fast_deploy.py --service $(SVC)

aws-fast-web:
	python scripts/aws/fast_deploy.py --service web

aws-fast-agent:
	python scripts/aws/fast_deploy.py --service agent

aws-fast-bakery:
	python scripts/aws/fast_deploy.py --service bakery

aws-fast-all:
	python scripts/aws/fast_deploy.py --service all

aws-scorecard-evidence:
	python scripts/qa/scorecard_evidence.py

aws-restore-drill:
	python scripts/aws/restore_drill.py

aws-approve-scale:
	python scripts/aws/approve_scale.py --confirm APPROVE_SCALE

aws-deploy:
	python scripts/aws/deploy_app.py

aws-restart:
	python scripts/aws/ops.py ssm-run -- "cd /opt/cloudiqs-demo/compose && . /opt/cloudiqs-demo/env.sh && docker compose -f compose.aws.yaml restart"

aws-health:
	python scripts/aws/ops.py ssm-run -- "curl -sf http://127.0.0.1/api/health; echo; curl -sf http://127.0.0.1:8001/health/ready || docker compose -f /opt/cloudiqs-demo/compose/compose.aws.yaml exec -T agent-api curl -sf http://127.0.0.1:8001/health/ready; echo; docker compose -f /opt/cloudiqs-demo/compose/compose.aws.yaml ps"

aws-logs:
	python scripts/aws/ops.py ssm-run -- "docker compose -f /opt/cloudiqs-demo/compose/compose.aws.yaml logs --tail=120"

aws-backup-demo:
	python scripts/aws/ops.py ssm-run -- "set -e; . /opt/cloudiqs-demo/env.sh; STAMP=$$(date -u +%Y%m%dT%H%M%SZ); aws s3 cp /opt/cloudiqs-demo/data/runtime.sqlite s3://$$BACKUP_BUCKET/sqlite/runtime-$$STAMP.sqlite; aws s3 cp /opt/cloudiqs-demo/data/app.sqlite s3://$$BACKUP_BUCKET/sqlite/app-$$STAMP.sqlite; echo backed-up-$$STAMP"

aws-restore-demo:
	@test "$(CONFIRM)" = "YES" || (echo "Refused: pass CONFIRM=YES"; exit 1)
	python scripts/aws/ops.py ssm-run -- "echo restore requires KEY=s3://bucket/... ; exit 1"

aws-reset-demo:
	@test "$(CONFIRM)" = "YES" || (echo "Refused: pass CONFIRM=YES"; exit 1)
	python scripts/aws/ops.py ssm-run -- "set -e; cd /opt/cloudiqs-demo/compose; docker compose -f compose.aws.yaml stop agent-api enterprise-mock-api; cp /opt/cloudiqs-demo/data/canonical/enterprise.sqlite /opt/cloudiqs-demo/data/runtime.sqlite; rm -f /opt/cloudiqs-demo/data/app.sqlite*; docker compose -f compose.aws.yaml up -d"

aws-destroy-demo:
	@test "$(CONFIRM_DESTROY)" = "CloudiQSDemo" || (echo "Refused: pass CONFIRM_DESTROY=CloudiQSDemo"; exit 1)
	python scripts/aws/ops.py destroy-guard --confirm CloudiQSDemo
	cd infra/cdk && npx cdk destroy --all --force

# ---- AgentCore (separated from web/DB deploys) ----
dev:
	python scripts/agentcore/helio_ops.py dev

deploy-agent:
	python scripts/agentcore/helio_ops.py deploy-agent

deploy-web:
	python scripts/agentcore/helio_ops.py deploy-web

deploy-all:
	python scripts/agentcore/helio_ops.py deploy-all

agentcore-status:
	python scripts/agentcore/helio_ops.py status

agentcore-logs:
	python scripts/agentcore/helio_ops.py logs

agentcore-rollback:
	python scripts/agentcore/helio_ops.py rollback

destroy-agentcore:
	python scripts/agentcore/helio_ops.py destroy-agentcore --confirm=$(CONFIRM)
