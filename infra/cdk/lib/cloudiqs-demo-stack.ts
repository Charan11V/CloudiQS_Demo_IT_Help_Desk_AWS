import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ssm from "aws-cdk-lib/aws-ssm";
import * as logs from "aws-cdk-lib/aws-logs";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatch_actions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subs from "aws-cdk-lib/aws-sns-subscriptions";
import * as budgets from "aws-cdk-lib/aws-budgets";
export interface CloudiQSDemoStackProps extends cdk.StackProps {
  /** Existing runtime instance profile name created by bootstrap (optional). */
  runtimeInstanceProfileName?: string;
  /** Budget notification email — leave empty to skip SNS-style notifications. */
  budgetEmail?: string;
  instanceType?: string;
  ebsSizeGiB?: number;
}

const PREFIX = "cloudiqs-demo";
const PROJECT_TAGS = {
  Project: "CloudiQSDemo",
  Environment: "Demo",
  ManagedBy: "CDK",
  Purpose: "HiringDemo",
};

export class CloudiQSDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: CloudiQSDemoStackProps = {}) {
    super(scope, id, props);

    const instanceTypeName = props.instanceType || "t4g.small";
    const ebsSize = props.ebsSizeGiB ?? 20;
    if (ebsSize > 30) {
      throw new Error("EBS > 30 GiB requires explicit approval");
    }
    const allowedTypes = new Set(["t4g.micro", "t4g.small", "t4g.medium", "t3.micro", "t3.small", "t3a.micro", "t3a.small"]);
    if (!allowedTypes.has(instanceTypeName)) {
      throw new Error(`Instance type ${instanceTypeName} not in cost-safe allowlist`);
    }

    // ---- Networking: 1 VPC, 1 public subnet, IGW, NO NAT ----
    const vpc = new ec2.Vpc(this, "Vpc", {
      vpcName: `${PREFIX}-vpc`,
      maxAzs: 1,
      natGateways: 0,
      subnetConfiguration: [
        {
          name: "public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
      ],
    });

    // ---- ECR repositories ----
    const lifecycle = {
      maxImageCount: 5,
      description: "Retain only recent demo images",
    };
    const webRepo = new ecr.Repository(this, "WebRepo", {
      repositoryName: `${PREFIX}-web`,
      imageScanOnPush: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      emptyOnDelete: true,
      lifecycleRules: [lifecycle],
    });
    const agentRepo = new ecr.Repository(this, "AgentRepo", {
      repositoryName: `${PREFIX}-agent-api`,
      imageScanOnPush: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      emptyOnDelete: true,
      lifecycleRules: [lifecycle],
    });
    const mockRepo = new ecr.Repository(this, "MockRepo", {
      repositoryName: `${PREFIX}-mock-api`,
      imageScanOnPush: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      emptyOnDelete: true,
      lifecycleRules: [lifecycle],
    });

    // ---- S3 backups (private, short retention) ----
    const backupBucket = new s3.Bucket(this, "BackupBucket", {
      bucketName: undefined, // let CloudFormation generate unique name
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      lifecycleRules: [{ expiration: cdk.Duration.days(14), id: "expire-demo-artifacts" }],
    });
    cdk.Tags.of(backupBucket).add("Name", `${PREFIX}-backups`);

    // ---- Log groups (7-day retention) ----
    const retention = logs.RetentionDays.ONE_WEEK;
    const webLog = new logs.LogGroup(this, "WebLogs", {
      logGroupName: `/cloudiqs-demo/web`,
      retention,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    const agentLog = new logs.LogGroup(this, "AgentLogs", {
      logGroupName: `/cloudiqs-demo/agent-api`,
      retention,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    const mockLog = new logs.LogGroup(this, "MockLogs", {
      logGroupName: `/cloudiqs-demo/mock-api`,
      retention,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ---- SSM parameters (Standard tier; deploy script upgrades secrets to SecureString) ----
    new ssm.StringParameter(this, "ParamSessionKey", {
      parameterName: `/${PREFIX}/APP_SESSION_SIGNING_KEY`,
      stringValue: "REPLACE_AT_DEPLOY",
      description: "Overwrite with SecureString before first public use",
      tier: ssm.ParameterTier.STANDARD,
    });
    new ssm.StringParameter(this, "ParamDemoSecret", {
      parameterName: `/${PREFIX}/DEMO_ACCESS_SECRET`,
      stringValue: "REPLACE_AT_DEPLOY",
      description: "Outer demo access gate secret - overwrite via deploy script",
      tier: ssm.ParameterTier.STANDARD,
    });
    new ssm.StringParameter(this, "ParamModel", {
      parameterName: `/${PREFIX}/BEDROCK_MODEL_ID`,
      stringValue: "amazon.nova-lite-v1:0",
      description: "Bedrock model ID selected after cost/quality benchmark",
      tier: ssm.ParameterTier.STANDARD,
    });
    new ssm.StringParameter(this, "ParamProvider", {
      parameterName: `/${PREFIX}/MODEL_PROVIDER`,
      stringValue: "bedrock",
      tier: ssm.ParameterTier.STANDARD,
    });
    new ssm.StringParameter(this, "ParamDemoNow", {
      parameterName: `/${PREFIX}/DEMO_NOW`,
      stringValue: "2026-10-31T10:00:00Z",
      tier: ssm.ParameterTier.STANDARD,
    });
    new ssm.StringParameter(this, "ParamLogLevel", {
      parameterName: `/${PREFIX}/LOG_LEVEL`,
      stringValue: "INFO",
      tier: ssm.ParameterTier.STANDARD,
    });
    // ---- Runtime IAM role (if not provided by bootstrap, create here) ----
    const runtimeRole = new iam.Role(this, "RuntimeRole", {
      roleName: "CloudiQSDemoRuntimeRole",
      assumedBy: new iam.ServicePrincipal("ec2.amazonaws.com"),
      description: "EC2 instance role for CloudiQS demo runtime (no long-lived keys)",
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMManagedInstanceCore"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("CloudWatchAgentServerPolicy"),
      ],
    });

    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockInvoke",
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:GetFoundationModel",
          "bedrock:ListFoundationModels",
        ],
        resources: ["*"], // Bedrock model ARNs vary by inference profile; scoped by account
        conditions: {
          StringEquals: { "aws:RequestedRegion": this.region },
        },
      })
    );
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "SsmReadDemoParams",
        actions: ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
        resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/${PREFIX}/*`],
      })
    );
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "EcrPull",
        actions: [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
        ],
        resources: ["*"],
      })
    );
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "S3BackupAccess",
        actions: ["s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject"],
        resources: [backupBucket.bucketArn, `${backupBucket.bucketArn}/*`],
      })
    );
    runtimeRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "CwLogs",
        actions: ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"],
        resources: [webLog.logGroupArn, agentLog.logGroupArn, mockLog.logGroupArn, `${webLog.logGroupArn}:*`, `${agentLog.logGroupArn}:*`, `${mockLog.logGroupArn}:*`],
      })
    );

    const instanceProfile = new iam.CfnInstanceProfile(this, "RuntimeInstanceProfile", {
      instanceProfileName: "CloudiQSDemoRuntimeInstanceProfile",
      roles: [runtimeRole.roleName],
    });

    // ---- Security group: HTTP from CloudFront / internet for origin; no SSH ----
    const sg = new ec2.SecurityGroup(this, "InstanceSg", {
      vpc,
      securityGroupName: `${PREFIX}-sg`,
      description: "CloudiQS demo EC2 - web origin only, no SSH",
      allowAllOutbound: true,
    });
    // Prefer CloudFront managed prefix list when available; also allow HTTPS/HTTP for bootstrap health
    sg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), "HTTP origin (restrict further with origin token)");
    // No port 22

    // Shared CloudFront→origin verification token (also written into instance env)
    const originVerifyValue = cdk.Fn.join("", [
      "cf-",
      cdk.Fn.select(2, cdk.Fn.split("/", this.stackId)),
    ]);

    // ---- EC2 Amazon Linux 2023 ARM ----
    const ami = ec2.MachineImage.latestAmazonLinux2023({
      cpuType: ec2.AmazonLinuxCpuType.ARM_64,
    });

    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      "set -euxo pipefail",
      "dnf update -y",
      "dnf install -y docker amazon-ssm-agent amazon-cloudwatch-agent jq awscli",
      "systemctl enable --now docker amazon-ssm-agent",
      "usermod -aG docker ec2-user || true",
      // Docker Compose plugin
      "mkdir -p /usr/local/lib/docker/cli-plugins",
      'curl -fsSL "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-aarch64" -o /usr/local/lib/docker/cli-plugins/docker-compose',
      "chmod +x /usr/local/lib/docker/cli-plugins/docker-compose",
      "mkdir -p /opt/cloudiqs-demo/data /opt/cloudiqs-demo/compose",
      // Persist path for SQLite
      "REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region || echo us-east-1)",
      "ACCOUNT=$(curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .accountId)",
      `cat > /opt/cloudiqs-demo/env.sh <<'EOF'
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
export ECR_WEB=${webRepo.repositoryUri}
export ECR_AGENT=${agentRepo.repositoryUri}
export ECR_MOCK=${mockRepo.repositoryUri}
export BACKUP_BUCKET=${backupBucket.bucketName}
export SSM_PREFIX=/${PREFIX}
export ORIGIN_VERIFY_TOKEN=${originVerifyValue}
EOF`,
      "chmod 755 /opt/cloudiqs-demo/env.sh",
      // Placeholder compose — replaced by make aws-deploy via SSM
      `cat > /opt/cloudiqs-demo/compose/compose.aws.yaml <<'EOF'
services:
  enterprise-mock-api:
    image: PLACEHOLDER_MOCK
    restart: unless-stopped
    environment:
      ENTERPRISE_DEMO_DB: /var/lib/helio/runtime.sqlite
    volumes:
      - /opt/cloudiqs-demo/data/mock:/var/lib/helio
    networks: [helio]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 10s
      timeout: 5s
      retries: 12
  agent-api:
    image: PLACEHOLDER_AGENT
    restart: unless-stopped
    environment:
      MODEL_PROVIDER: bedrock
      AWS_REGION: us-east-1
      APP_DB_PATH: /data/app.sqlite
      ENTERPRISE_API_URL: http://enterprise-mock-api:8000
      ENABLE_FAULT_INJECTION: "0"
      LOG_LEVEL: INFO
    volumes:
      - /opt/cloudiqs-demo/data/agent:/data
      - /opt/cloudiqs-demo/data/pack:/pack:ro
    depends_on:
      enterprise-mock-api:
        condition: service_healthy
    networks: [helio]
  web:
    image: PLACEHOLDER_WEB
    restart: unless-stopped
    ports:
      - "80:3000"
    environment:
      AGENT_API_URL: http://agent-api:8001
      HOSTNAME: "0.0.0.0"
      PORT: "3000"
      DEMO_GATE_ENABLED: "1"
    depends_on:
      - agent-api
    networks: [helio]
networks:
  helio:
    driver: bridge
EOF`,
      "echo 'Bootstrap complete - await SSM deploy for real images' > /opt/cloudiqs-demo/BOOTSTRAP.txt"
    );

    const instance = new ec2.Instance(this, "DemoInstance", {
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      instanceType: new ec2.InstanceType(instanceTypeName),
      machineImage: ami,
      securityGroup: sg,
      role: runtimeRole,
      userData,
      blockDevices: [
        {
          deviceName: "/dev/xvda",
          volume: ec2.BlockDeviceVolume.ebs(ebsSize, {
            volumeType: ec2.EbsDeviceVolumeType.GP3,
            encrypted: true,
            deleteOnTermination: true,
          }),
        },
      ],
      requireImdsv2: true,
      associatePublicIpAddress: true,
      detailedMonitoring: false,
    });
    // Ensure instance profile exists first
    instance.node.addDependency(instanceProfile);
    cdk.Tags.of(instance).add("Name", `${PREFIX}-ec2`);
    Object.entries(PROJECT_TAGS).forEach(([k, v]) => cdk.Tags.of(instance).add(k, v));

    // CloudFront deferred: new accounts often require AWS Support verification
    // before creating distributions. Demo is reachable via EC2 public HTTP until then.
    // Re-enable Distribution after account verification (see docs/AWS_DEPLOYMENT.md).
    void originVerifyValue;
    void cloudfront;
    void origins;

    // ---- CloudWatch dashboard ----
    const dashboard = new cloudwatch.Dashboard(this, "Dashboard", {
      dashboardName: "CloudiQSDemo",
    });
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: "EC2 CPUUtilization",
        left: [
          new cloudwatch.Metric({
            namespace: "AWS/EC2",
            metricName: "CPUUtilization",
            dimensionsMap: { InstanceId: instance.instanceId },
            statistic: "Average",
            period: cdk.Duration.minutes(5),
          }),
        ],
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: "EC2 StatusCheckFailed",
        left: [
          new cloudwatch.Metric({
            namespace: "AWS/EC2",
            metricName: "StatusCheckFailed",
            dimensionsMap: { InstanceId: instance.instanceId },
            statistic: "Maximum",
            period: cdk.Duration.minutes(5),
          }),
        ],
        width: 12,
      })
    );

    // ---- Approval-gated scale notify (alarm → SNS; NO auto scale-out) ----
    const scaleTopic = new sns.Topic(this, "ScaleNotifyTopic", {
      topicName: `${PREFIX}-scale-notify`,
      displayName: "CloudiQS demo scale approval notify",
    });
    const notifyEmail =
      props.budgetEmail ||
      process.env.CLOUDIQS_BUDGET_EMAIL ||
      process.env.CLOUDIQS_SCALE_EMAIL;
    if (notifyEmail) {
      scaleTopic.addSubscription(new subs.EmailSubscription(notifyEmail));
    }
    const cpuAlarm = new cloudwatch.Alarm(this, "HighCpuAlarm", {
      alarmName: `${PREFIX}-cpu-high`,
      alarmDescription:
        "Demo EC2 CPU high — notify human; do NOT auto-scale. Approve via scripts/aws/approve_scale.py",
      metric: new cloudwatch.Metric({
        namespace: "AWS/EC2",
        metricName: "CPUUtilization",
        dimensionsMap: { InstanceId: instance.instanceId },
        statistic: "Average",
        period: cdk.Duration.minutes(5),
      }),
      threshold: 70,
      evaluationPeriods: 3,
      datapointsToAlarm: 3,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    cpuAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(scaleTopic));
    new cdk.CfnOutput(this, "ScaleNotifyTopicArn", { value: scaleTopic.topicArn });

    // ---- AWS Budget (account-level demo guardrails) ----
    const budgetEmail = props.budgetEmail || process.env.CLOUDIQS_BUDGET_EMAIL;
    const notifications: budgets.CfnBudget.NotificationWithSubscribersProperty[] = [];
    if (budgetEmail) {
      for (const [threshold, tType] of [
        [10, "ACTUAL"],
        [25, "ACTUAL"],
        [50, "ACTUAL"],
        [75, "ACTUAL"],
        [90, "FORECASTED"],
      ] as const) {
        notifications.push({
          notification: {
            notificationType: tType,
            comparisonOperator: "GREATER_THAN",
            threshold,
            thresholdType: "ABSOLUTE_VALUE",
          },
          subscribers: [{ subscriptionType: "EMAIL", address: budgetEmail }],
        });
      }
    }

    new budgets.CfnBudget(this, "DemoBudget", {
      budget: {
        budgetName: "CloudiQSDemo-Monthly",
        budgetType: "COST",
        timeUnit: "MONTHLY",
        budgetLimit: { amount: 100, unit: "USD" },
        costFilters: undefined,
      },
      notificationsWithSubscribers: notifications.length ? notifications : undefined,
    });

    // ---- Outputs ----
    new cdk.CfnOutput(this, "DemoUrl", {
      value: `http://${instance.instancePublicDnsName}`,
      description: "Public demo URL (HTTP via EC2 until CloudFront account verification)",
    });
    new cdk.CfnOutput(this, "CloudFrontStatus", {
      value: "DEFERRED_PENDING_ACCOUNT_VERIFICATION",
      description: "Open AWS Support to verify account, then re-add CloudFront for HTTPS",
    });
    new cdk.CfnOutput(this, "InstanceId", { value: instance.instanceId });
    new cdk.CfnOutput(this, "InstancePublicDns", { value: instance.instancePublicDnsName });
    new cdk.CfnOutput(this, "BackupBucketName", { value: backupBucket.bucketName });
    new cdk.CfnOutput(this, "WebRepoUri", { value: webRepo.repositoryUri });
    new cdk.CfnOutput(this, "AgentRepoUri", { value: agentRepo.repositoryUri });
    new cdk.CfnOutput(this, "MockRepoUri", { value: mockRepo.repositoryUri });
    new cdk.CfnOutput(this, "RuntimeRoleArn", { value: runtimeRole.roleArn });
    new cdk.CfnOutput(this, "DashboardName", { value: "CloudiQSDemo" });
    new cdk.CfnOutput(this, "Region", { value: this.region });
  }
}
