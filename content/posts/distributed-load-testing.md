---
title: "How I Built a Distributed Load Testing Platform on AWS"
date: 2026-09-13
draft: false
author: Ajay Dhungel
description: "A walkthrough of building a distributed load testing service on ECS Fargate — k6 workers that autoscale from zero based on SQS queue depth, with a FastAPI control plane and Grafana dashboards."
tags: ["aws", "devops", "infrastructure", "load-testing"]
tech: ["aws", "docker", "iac", "github-actions"]
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Why I Built This

Load testing usually lives at the end of a project, when everyone is too tired to care about it properly. You spin up a single machine, run k6 or wrk for a few minutes, watch the numbers, and call it done.

That works fine until you need to generate serious traffic. A single machine becomes the bottleneck before your actual service does, and suddenly your load test is testing the load tester, not the thing you care about.

I wanted something that scales to real production-level traffic without babysitting a fleet of EC2 instances. Submit a test via an API, workers spin up automatically, run the test, publish metrics to a dashboard. No manual infrastructure, no SSH sessions, no teardown scripts. Just an API call and a result.

This is that system.

---

## What You'll Build

A distributed load testing platform on AWS with:

- A **FastAPI control plane** running on ECS Fargate behind an Application Load Balancer
- A **k6 worker service** that scales from zero to 50 tasks based on SQS queue depth
- **DynamoDB** for job metadata and status tracking
- **SQS** as the job queue between the control plane and workers
- **CloudWatch EMF** for structured metrics (p50, p95, p99, throughput, error rate)
- **Grafana** on ECS Fargate with a pre-provisioned CloudWatch dashboard
- **AWS CDK** in TypeScript for all infrastructure, deployed via GitHub Actions with OIDC

The architecture looks like this:

```
User → Control Plane API (ALB → ECS Fargate)
           │
           ├── DynamoDB  (job metadata + results)
           └── SQS       (job queue)
                │
                ├── CloudWatch Alarm (queue depth ≥ 1)
                │       └── App Auto Scaling → Worker Service (0 → 50 tasks)
                │
                └── Worker Tasks (k6)
                        ├── DynamoDB  (status updates + results)
                        ├── S3        (raw k6 JSON summary)
                        └── CloudWatch EMF → Grafana
```

The interesting design choice is the autoscaling trigger. Rather than scaling on CPU or memory, workers scale on queue depth. When a job lands in SQS, a CloudWatch alarm fires and the ECS service scales up from zero. When the queue drains, it scales back down. You pay for workers only while tests are actually running.

## Prerequisites

To follow along you will need:

- An AWS account with permissions to create ECS, DynamoDB, SQS, S3, IAM, and CloudWatch resources
- AWS CDK installed (`npm install -g aws-cdk`) and bootstrapped in your account
- Docker installed and running
- Node.js 18+ and Python 3.11+
- A GitHub repository with OIDC configured for deployments

---

## The Infrastructure: Four CDK Stacks

All infrastructure lives in `infra/` as TypeScript CDK, split into four stacks that deploy in dependency order. This separation keeps each stack focused and makes partial deployments clean. If you only change Grafana, you only redeploy `GrafanaStack`.

### InfraStack: The Foundation

`InfraStack` creates everything shared: VPC, ECR repositories, DynamoDB table, SQS queue, S3 results bucket, and IAM task roles.

The DynamoDB table uses `testId` as the partition key, `createdAt` as the sort key, and a GSI on `status` so you can query all running tests without a full table scan.

```typescript
const table = new dynamodb.Table(this, 'LoadTestsTable', {
  tableName: 'load-tests',
  partitionKey: { name: 'testId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'createdAt', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
});

table.addGlobalSecondaryIndex({
  indexName: 'status-index',
  partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
});
```

The SQS queue gets a dead-letter queue with `maxReceiveCount: 3`. If a worker crashes mid-test three times, the job moves to the DLQ rather than cycling forever. It is the kind of thing you are glad you put in before you need it.

For IAM, I created two task roles with least-privilege policies. `ControlPlaneTaskRole` can write to DynamoDB and SQS. `WorkerTaskRole` can read from SQS, write to DynamoDB and S3, and publish CloudWatch metrics. Neither has anything broader than it needs.

### ControlPlaneStack: The API

The control plane is a FastAPI app with two endpoints: `POST /tests` to submit a job and `GET /tests/{id}` to check status. It runs as a single Fargate task behind an Application Load Balancer.

```typescript
const service = new ecs.FargateService(this, 'ControlPlaneService', {
  cluster,
  taskDefinition,
  desiredCount: 1,
  assignPublicIp: false,
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
});
```

One task is enough here. The control plane is stateless — all state lives in DynamoDB and SQS — so scaling it out is trivial if needed, but a single task handles the submission rate of a load testing service without issue.

On `POST /tests`, the API writes a `PENDING` record to DynamoDB, puts a message on SQS, and returns the `testId`. The client polls `GET /tests/{id}` to watch the status transition from `PENDING` to `RUNNING` to `COMPLETED`.

```python
@router.post("/tests", response_model=TestResponse)
async def create_test(body: CreateTestRequest):
    test_id = str(uuid.uuid4())
    await dynamodb_client.put_item(test_id, status="PENDING", config=body.dict())
    await sqs_client.send_message({"testId": test_id, **body.dict()})
    return TestResponse(testId=test_id, status="PENDING")
```

### WorkerStack: k6 on Fargate

The worker is where load generation actually happens. Each task polls SQS for a job, generates a k6 script from the job parameters, runs it, and writes results back to DynamoDB and S3.

The service starts at `desiredCount: 0`. No workers run when the system is idle — the autoscaling stack handles bringing them up.

```typescript
const workerService = new ecs.FargateService(this, 'WorkerService', {
  cluster,
  taskDefinition: workerTaskDef,
  desiredCount: 0,
  assignPublicIp: false,
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
});
```

The worker's main loop is a straightforward polling pattern: receive a message, mark the job `RUNNING`, run k6, emit metrics, write the summary to S3, mark the job `COMPLETED`, delete the SQS message.

```python
while True:
    message = sqs.receive_message()
    if not message:
        time.sleep(5)
        continue

    job = json.loads(message['Body'])
    dynamodb.update_status(job['testId'], 'RUNNING')

    result = k6_runner.run(job)
    metrics_emitter.emit(job['testId'], result)

    s3.upload_summary(job['testId'], result)
    dynamodb.update_status(job['testId'], 'COMPLETED', result=result)
    sqs.delete_message(message['ReceiptHandle'])
```

Rather than storing k6 scripts as files, the worker generates them at runtime from the structured job config. This keeps the API clean — you submit a JSON payload describing the test, not a script file.

### AutoscalingStack: Scale on Queue Depth

This is the part I found most satisfying to build. The autoscaling is driven entirely by SQS queue depth, not CPU or memory.

A CloudWatch metric alarm watches `ApproximateNumberOfMessagesVisible` on the SQS queue. When it goes above zero, the alarm fires and triggers a step scaling policy on the worker ECS service.

```typescript
const scalingTarget = new appscaling.ScalableTarget(this, 'WorkerScalingTarget', {
  serviceNamespace: appscaling.ServiceNamespace.ECS,
  resourceId: `service/${cluster.clusterName}/${workerService.serviceName}`,
  scalableDimension: 'ecs:service:DesiredCount',
  minCapacity: 0,
  maxCapacity: 50,
});

scalingTarget.scaleOnMetric('ScaleOnQueueDepth', {
  metric: queue.metricApproximateNumberOfMessagesVisible(),
  scalingSteps: [
    { upper: 0, change: -50 },
    { lower: 1, change: +5 },
    { lower: 10, change: +20 },
  ],
  adjustmentType: appscaling.AdjustmentType.CHANGE_IN_CAPACITY,
});
```

A small queue depth spins up five workers. A deeper queue adds twenty more on top of that. When the queue drains back to zero, workers scale back down. The latency from job submission to worker start is roughly 60 to 90 seconds — one CloudWatch evaluation period plus Fargate cold start time. For a load testing service where tests run for minutes, that is a perfectly acceptable trade-off.

---

## Metrics: CloudWatch EMF

Rather than calling `PutMetricData`, the worker uses Embedded Metric Format. EMF lets you emit structured JSON logs that CloudWatch automatically parses into metrics. No extra API calls, no metric clients in the hot path — just a structured log entry.

```python
def emit(self, test_id: str, result: dict):
    metric = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": "LoadTest",
                "Dimensions": [["TestId"]],
                "Metrics": [
                    {"Name": "p50", "Unit": "Milliseconds"},
                    {"Name": "p95", "Unit": "Milliseconds"},
                    {"Name": "p99", "Unit": "Milliseconds"},
                    {"Name": "throughput", "Unit": "Count/Second"},
                    {"Name": "errorRate", "Unit": "Percent"},
                ]
            }]
        },
        "TestId": test_id,
        "p50": result["p50"],
        "p95": result["p95"],
        "p99": result["p99"],
        "throughput": result["throughput"],
        "errorRate": result["error_rate"],
    }
    print(json.dumps(metric))
```

That `print` call is the entire metric emission. CloudWatch Logs picks it up from the Fargate task logs and creates the metrics automatically. I like this pattern because it keeps the worker code simple and the metrics appear in CloudWatch without any extra plumbing.

---

## Grafana: Pre-Provisioned Dashboards

Grafana runs as its own Fargate service with a custom Docker image that bakes in the CloudWatch datasource and a pre-built dashboard. When the container starts, everything is already configured — no manual setup, no clicking through the UI.

```yaml
# provisioning/datasources/cloudwatch.yaml
apiVersion: 1
datasources:
  - name: CloudWatch
    type: cloudwatch
    jsonData:
      authType: default
      defaultRegion: us-east-1
```

The `authType: default` means Grafana authenticates to CloudWatch using the ECS task role. No access keys, no secrets in environment variables. The `GrafanaTaskRole` just needs `cloudwatch:GetMetricData` and `cloudwatch:ListMetrics`.

The dashboard JSON lives in `grafana/dashboards/loadtest.json` and is mounted via the file provider. Submit a test, wait for it to complete, open Grafana. You will see p50/p95/p99 latency, throughput, and error rate broken down by `TestId`, so you can compare multiple runs side by side.

And just like that, you have a production-grade observability layer with zero Grafana configuration on first deploy.

---

## CI/CD: GitHub Actions with OIDC

The deployment pipeline builds and pushes Docker images to ECR, then deploys the CDK stacks. Authentication uses OIDC — no long-lived AWS access keys stored as GitHub secrets.

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: us-east-1

- name: Deploy infrastructure
  run: npx cdk deploy InfraStack --require-approval never

- name: Build and push images
  run: |
    docker build -t $ECR_REGISTRY/loadtest/control-plane:$SHA ./control-plane
    docker push $ECR_REGISTRY/loadtest/control-plane:$SHA

- name: Deploy application stacks
  run: |
    npx cdk deploy ControlPlaneStack WorkerStack AutoscalingStack GrafanaStack \
      --require-approval never
```

Deploy only runs on pushes to `main`. On every PR, the CI workflow runs pytest for the control plane and worker, builds the Docker images without pushing, and runs CDK assertion tests against the stacks.

I keep `InfraStack` as a separate deploy step from the application stacks. Shared resources like DynamoDB, SQS, and IAM roles change infrequently, and separating them means an application stack failure does not leave the foundation in a partial state.

---

## Running a Test

Once deployed, submitting a test is one command:

```bash
curl -X POST http://<alb-dns>/tests \
  -H "Content-Type: application/json" \
  -d '{
    "target": "https://your-service.com/api/endpoint",
    "vus": 50,
    "duration": "2m",
    "thresholds": {
      "http_req_duration": ["p95<500"]
    }
  }'
```

You get back a `testId`. Poll `GET /tests/{id}` to watch the status. Within about 90 seconds the workers are up and the test is running. When it finishes, check the Grafana dashboard.

---

## A Few Things Worth Knowing

The 60 to 90 second cold start is the main trade-off with this design. If you need sub-10-second worker startup, you would need a minimum of warm workers, which changes the cost profile. For most load testing use cases where tests run for several minutes, the startup latency is acceptable.

The Grafana instance in this setup is public-facing with no authentication. For anything beyond a personal project, put it behind a Cognito-authenticated ALB or enable Grafana's built-in auth.

Each worker task runs a single k6 process. For very high concurrency targets you could increase the task CPU and memory allocation or run multiple workers per test. I kept it simple here — one task, one test, clean accounting.

---

## The Repo

The full project is on GitHub at [ajaydhungel7/distributed-loadtesting](https://github.com/ajaydhungel7/distributed-loadtesting). The README covers CDK bootstrap, deployment order, and how to wire up the GitHub OIDC role.

If you are building services on AWS and want a load testing setup that actually scales with your traffic requirements, this is a solid starting point.

---

That's all for now! Thank you so much for making it to the end.
