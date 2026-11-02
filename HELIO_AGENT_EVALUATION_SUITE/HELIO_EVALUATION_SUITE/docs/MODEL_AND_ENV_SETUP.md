# Model, Environment, Cost and Security Setup

## Agent model

Run the HELIO app in Docker locally. `strands-agents` invokes Amazon Bedrock only when AWS credentials/permissions, supported region and actual model ID are configured. Otherwise a separate simulator path must be labelled as simulation, not generative inference. The agent has access only to tenant-scoped mock enterprise tools.

## Evaluator judge model

The evaluator is a separate process that reads the private gold file and recorded agent responses. Prefer a different capable model than the agent to reduce correlated errors. AWS Bedrock Converse is supported in `tools/judge.py` with `boto3`, or use an OpenAI-compatible `/v1/chat/completions` endpoint. Model availability, fees and regions vary; configure your supported model ID rather than hardcoding a deprecated ID.

Example Python packages:

```bash
pip install boto3  # only if you choose the Bedrock AI judge
```

For a local OpenAI-compatible model endpoint:

```bash
export JUDGE_API_URL=http://127.0.0.1:11434/v1/chat/completions
export JUDGE_MODEL_ID=YOUR_INSTALLED_JUDGE_MODEL
```

For Bedrock:

```bash
export AWS_REGION=YOUR_REGION
export JUDGE_MODEL_ID=YOUR_BEDROCK_CONVERSE_MODEL
```

## Cost control

Start with 3 smoke cases, then 15, then core regression. Most cases have multiple tool calls and some have three turns. Track actual token usage and model costs; use concurrency=1 initially, bounded retries, timeouts, and model request budget. Do not automatically run a large paid benchmark without explicit configuration.

## Test isolation

- Agent container mounts public fixtures and enterprise mock API, **not** `cases/private_oracle`.
- Evaluator container mounts public case metadata, private oracle and outputs; it can access the agent HTTP API but not the agent's secrets or AWS credentials unless Bedrock judging is chosen.
- Never store AWS credentials or private real data in the ZIP, GitHub, result export or browser static assets.
- The mock system is synthetic, including demo tokens; it is not suitable for public internet exposure or live account remediation.
- Avoid using an LLM judge as a substitute for code-based authorisation or state integrity tests.
