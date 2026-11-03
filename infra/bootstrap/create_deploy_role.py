#!/usr/bin/env python3
"""Bootstrap CloudiQSDemoDeployRole with least-privilege, cost-safe guardrails.

Run once with a temporary authenticated bootstrap principal:

  aws login
  python infra/bootstrap/create_deploy_role.py

Does NOT store long-lived access keys. Creates an IAM role that the bootstrap
session can assume via profile cloudiqs-demo-deployer.
"""
from __future__ import annotations

import json
import sys

import boto3
from botocore.exceptions import ClientError

ROLE_NAME = "CloudiQSDemoDeployRole"
BOUNDARY_NAME = "CloudiQSDemoPermissionsBoundary"
PREFIX = "cloudiqs-demo"
PROJECT = "CloudiQSDemo"
REGION = "us-east-1"


def account_id(sts) -> str:
    return sts.get_caller_identity()["Account"]


def principal_arn(sts) -> str:
    return sts.get_caller_identity()["Arn"]


def trust_policy(bootstrap_arn: str) -> dict:
    # Allow the current bootstrap principal (user/role session) to assume
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BootstrapAssume",
                "Effect": "Allow",
                "Principal": {"AWS": bootstrap_arn.split("/")[0].replace(":sts:", ":iam:").replace("assumed-role", "role")
                              if ":assumed-role/" in bootstrap_arn
                              else (bootstrap_arn if ":user/" in bootstrap_arn or ":root" in bootstrap_arn
                                    else bootstrap_arn)},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"sts:ExternalId": "CloudiQSDemo"},
                },
            }
        ],
    }


def normalize_principal(arn: str, acct: str) -> str:
    """Map STS assumed-role ARN to IAM role ARN; keep IAM user ARN as-is."""
    if ":assumed-role/" in arn:
        # arn:aws:sts::ACCT:assumed-role/RoleName/Session
        parts = arn.split(":")
        name = arn.split("/")[1]
        return f"arn:aws:iam::{acct}:role/{name}"
    if arn.endswith(":root") or ":user/" in arn or ":role/" in arn:
        return arn
    # Federated / login sessions often look like assumed-role or special principals —
    # fall back to account root for bootstrap trust (tighten after first assume).
    return f"arn:aws:iam::{acct}:root"


def permissions_boundary(acct: str) -> dict:
    """Hard cost guardrails — deny expensive services and large instances."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowDemoTaggedOrPrefix",
                "Effect": "Allow",
                "Action": [
                    "cloudformation:*",
                    "ec2:*",
                    "ecr:*",
                    "s3:*",
                    "ssm:*",
                    "ssmmessages:*",
                    "ec2messages:*",
                    "logs:*",
                    "cloudwatch:*",
                    "cloudfront:*",
                    "iam:Get*",
                    "iam:List*",
                    "iam:PassRole",
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:DeleteRolePolicy",
                    "iam:CreateInstanceProfile",
                    "iam:AddRoleToInstanceProfile",
                    "iam:RemoveRoleFromInstanceProfile",
                    "iam:DeleteInstanceProfile",
                    "iam:TagRole",
                    "iam:UntagRole",
                    "iam:TagInstanceProfile",
                    "budgets:*",
                    "ce:Get*",
                    "ce:Describe*",
                    "ce:List*",
                    "pricing:GetProducts",
                    "bedrock:List*",
                    "bedrock:Get*",
                    "bedrock:InvokeModel*",
                    "sts:GetCallerIdentity",
                    "sts:AssumeRole",
                    "tag:GetResources",
                    "tag:TagResources",
                    "tag:UntagResources",
                ],
                "Resource": "*",
            },
            {
                "Sid": "DenyExpensiveInfrastructure",
                "Effect": "Deny",
                "Action": [
                    "eks:*",
                    "rds:*",
                    "aurora:*",
                    "es:*",
                    "opensearch:*",
                    "elasticache:*",
                    "redshift:*",
                    "kafka:*",
                    "sagemaker:*",
                    "ec2:CreateNatGateway",
                    "ec2:AllocateHosts",
                    "elasticloadbalancing:CreateLoadBalancer",
                    "bedrock:CreateProvisionedModelThroughput",
                ],
                "Resource": "*",
            },
            {
                "Sid": "DenyLargeInstances",
                "Effect": "Deny",
                "Action": ["ec2:RunInstances"],
                "Resource": f"arn:aws:ec2:{REGION}:{acct}:instance/*",
                "Condition": {
                    "StringNotEquals": {
                        "ec2:InstanceType": [
                            "t4g.micro",
                            "t4g.small",
                            "t4g.medium",
                            "t3.micro",
                            "t3.small",
                            "t3a.micro",
                            "t3a.small",
                        ]
                    }
                },
            },
            {
                "Sid": "RestrictPassRole",
                "Effect": "Deny",
                "Action": "iam:PassRole",
                "Resource": "*",
                "Condition": {
                    "StringNotLike": {
                        "iam:PassedToService": [
                            "ec2.amazonaws.com",
                            "ssm.amazonaws.com",
                            "cloudformation.amazonaws.com",
                        ]
                    }
                },
            },
        ],
    }


def deploy_policy(acct: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "CoreDeploy",
                "Effect": "Allow",
                "Action": [
                    "cloudformation:*",
                    "ec2:*",
                    "ecr:*",
                    "s3:*",
                    "ssm:*",
                    "logs:*",
                    "cloudwatch:*",
                    "cloudfront:*",
                    "budgets:*",
                    "ce:GetCostAndUsage",
                    "ce:GetCostForecast",
                    "pricing:GetProducts",
                    "bedrock:ListFoundationModels",
                    "bedrock:GetFoundationModel",
                    "sts:GetCallerIdentity",
                    "iam:GetRole",
                    "iam:GetRolePolicy",
                    "iam:ListRolePolicies",
                    "iam:ListAttachedRolePolicies",
                    "iam:GetInstanceProfile",
                    "iam:PassRole",
                    "iam:CreateServiceLinkedRole",
                    "tag:GetResources",
                ],
                "Resource": "*",
            },
            {
                "Sid": "PassOnlyRuntimeRoles",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": [
                    f"arn:aws:iam::{acct}:role/CloudiQSDemoRuntimeRole",
                    f"arn:aws:iam::{acct}:role/cdk-*",
                    f"arn:aws:iam::{acct}:role/{PREFIX}-*",
                ],
            },
            {
                "Sid": "ManageDemoRoles",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:DeleteRolePolicy",
                    "iam:TagRole",
                    "iam:CreateInstanceProfile",
                    "iam:DeleteInstanceProfile",
                    "iam:AddRoleToInstanceProfile",
                    "iam:RemoveRoleFromInstanceProfile",
                    "iam:TagInstanceProfile",
                ],
                "Resource": [
                    f"arn:aws:iam::{acct}:role/CloudiQSDemo*",
                    f"arn:aws:iam::{acct}:instance-profile/CloudiQSDemo*",
                    f"arn:aws:iam::{acct}:role/cdk-*",
                    f"arn:aws:iam::{acct}:role/{PREFIX}-*",
                ],
            },
        ],
    }


def put_profile(role_arn: str) -> None:
    import configparser
    from pathlib import Path

    cfg_path = Path.home() / ".aws" / "config"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    if cfg_path.exists():
        parser.read(cfg_path)
    section = "profile cloudiqs-demo-deployer"
    if section not in parser:
        parser.add_section(section)
    parser[section]["role_arn"] = role_arn
    parser[section]["source_profile"] = "default"
    parser[section]["external_id"] = "CloudiQSDemo"
    parser[section]["region"] = REGION
    with cfg_path.open("w", encoding="utf-8") as fh:
        parser.write(fh)
    print(f"Wrote profile cloudiqs-demo-deployer -> {role_arn}")


def main() -> int:
    session = boto3.Session(region_name=REGION)
    sts = session.client("sts")
    iam = session.client("iam")

    ident = sts.get_caller_identity()
    acct = ident["Account"]
    caller = ident["Arn"]
    print(f"Bootstrap principal: {caller}")
    print(f"Account: {acct}")

    trust_principal = normalize_principal(caller, acct)
    print(f"Trust principal: {trust_principal}")

    # Permissions boundary
    try:
        iam.create_policy(
            PolicyName=BOUNDARY_NAME,
            PolicyDocument=json.dumps(permissions_boundary(acct)),
            Description="Cost/safety guardrails for CloudiQS demo deploy role",
            Tags=[
                {"Key": "Project", "Value": PROJECT},
                {"Key": "ManagedBy", "Value": "Bootstrap"},
            ],
        )
        print(f"Created permissions boundary {BOUNDARY_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        print(f"Permissions boundary {BOUNDARY_NAME} already exists — updating")
        versions = iam.list_policy_versions(PolicyArn=f"arn:aws:iam::{acct}:policy/{BOUNDARY_NAME}")["Versions"]
        if len(versions) >= 5:
            for v in versions:
                if not v["IsDefaultVersion"]:
                    iam.delete_policy_version(
                        PolicyArn=f"arn:aws:iam::{acct}:policy/{BOUNDARY_NAME}",
                        VersionId=v["VersionId"],
                    )
                    break
        iam.create_policy_version(
            PolicyArn=f"arn:aws:iam::{acct}:policy/{BOUNDARY_NAME}",
            PolicyDocument=json.dumps(permissions_boundary(acct)),
            SetAsDefault=True,
        )

    boundary_arn = f"arn:aws:iam::{acct}:policy/{BOUNDARY_NAME}"
    assume = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": trust_principal},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"sts:ExternalId": "CloudiQSDemo"}},
            }
        ],
    }

    try:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume),
            Description="Least-privilege deployer for CloudiQS HELIO demo",
            PermissionsBoundary=boundary_arn,
            Tags=[
                {"Key": "Project", "Value": PROJECT},
                {"Key": "Environment", "Value": "Demo"},
                {"Key": "ManagedBy", "Value": "Bootstrap"},
                {"Key": "Purpose", "Value": "HiringDemo"},
            ],
            MaxSessionDuration=3600,
        )["Role"]
        print(f"Created {ROLE_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        print(f"{ROLE_NAME} exists — updating trust + boundary")
        iam.update_assume_role_policy(RoleName=ROLE_NAME, PolicyDocument=json.dumps(assume))
        iam.put_role_permissions_boundary(RoleName=ROLE_NAME, PermissionsBoundary=boundary_arn)
        role = iam.get_role(RoleName=ROLE_NAME)["Role"]

    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="CloudiQSDemoDeployInline",
        PolicyDocument=json.dumps(deploy_policy(acct)),
    )
    print("Attached inline deploy policy")

    role_arn = role["Arn"]
    put_profile(role_arn)

    # Verify assume
    try:
        assumed = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="cloudiqs-bootstrap-verify",
            ExternalId="CloudiQSDemo",
        )
        print("AssumeRole OK:", assumed["AssumedRoleUser"]["Arn"])
    except ClientError as e:
        print("WARNING: AssumeRole verification failed:", e)
        print("You may need to allow the bootstrap principal in the trust policy manually.")
        return 2

    print("\nNext:")
    print("  aws sts get-caller-identity --profile cloudiqs-demo-deployer")
    print("  Then continue CDK deploy with AWS_PROFILE=cloudiqs-demo-deployer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
