.PHONY: up down reset-demo logs smoke-bedrock eval test-mock test-agent

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
	@test -n "$$AWS_ACCESS_KEY_ID$$AWS_BEARER_TOKEN_BEDROCK" || (echo "No AWS credentials configured"; exit 1)
	MODEL_PROVIDER=bedrock docker compose up -d agent-api
	docker compose exec agent-api python -c "from app.agent.factory import get_provider_info; print(get_provider_info())"
