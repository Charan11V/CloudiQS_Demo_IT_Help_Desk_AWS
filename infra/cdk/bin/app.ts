#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { CloudiQSDemoStack } from "../lib/cloudiqs-demo-stack";

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || "us-east-1",
};

const tags = {
  Project: "CloudiQSDemo",
  Environment: "Demo",
  ManagedBy: "CDK",
  Purpose: "HiringDemo",
};

const stack = new CloudiQSDemoStack(app, "CloudiQSDemoStack", {
  env,
  description:
    "CloudiQS / Agentic Bakery-inspired HELIO IT helpdesk demo (independent prototype)",
  tags,
});

Object.entries(tags).forEach(([k, v]) => cdk.Tags.of(stack).add(k, v));

app.synth();
