---
title: "Scaling AI Agents on AWS with Queue-Based Autoscaling"
date: 2026-09-13
draft: true
author: Ajay Dhungel
description: "How I built an elastic AI agent platform on AWS where each user request spins up an isolated agent session on ECS Fargate — scaling from zero based on queue depth, with traceable session identity per container."
tags: ["aws", "devops", "infrastructure", "ai"]
tech: ["aws", "docker", "iac", "github-actions"]
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Why I Built This

AI agent workloads are bursty. You might have zero requests for an hour and then dozens land at the same time. Each one needs its own session — its own context, its own API calls, its own results. Running them sequentially is too slow. Running always-on workers waiting for requests is too expensive.

What you want is workers that appear when there is work and disappear when there is not — and a way to trace exactly which session handled which request and returned what result.

I built a platform where each user request becomes an SQS message. Workers consume messages, run an AI agent, and write results back. The queue depth drives how many workers are alive at any moment. Each worker task gets a session identity from ECS at startup, so every result, log line, and metric is tied to the specific container that produced it.

This is that system.

---

## What You'll Build

A distributed AI agent platform on AWS with:

- A **FastAPI control plane** running on ECS Fargate behind an Application Load Balancer
- A **worker service** that scales from zero to 100 tasks based on SQS queue depth — each task is an isolated agent session
- **Session identity** via ECS task metadata, so every result and metric is traceable to the container that produced it
- **DynamoDB** for job metadata and status tracking
- **Two SQS queues** — one for job metadata, one as the agent request queue workers consume from
- **CloudWatch EMF** for structured metrics (total processed, avg agent response time per session)
- **Grafana** on ECS Fargate with a pre-provisioned CloudWatch dashboard
- **AWS CDK** in TypeScript for all infrastructure, deployed via GitHub Actions with OIDC

The architecture looks like this:

```
User → Control Plane API (ALB → ECS Fargate)
           │
           ├── DynamoDB              (job metadata + status)
           └── SQS loadtest-target   (one message per agent request)
                │
                ├── CloudWatch Alarm (queue depth ≥ 1) → bootstrap 1 worker
                │
                ├── Target Tracking Policy (500 msgs/worker) → 0–100 tasks
                │
                └── Worker Tasks  [each with a unique session ID]
                        ├── Agent logic  (your AI workload)
                        ├── DynamoDB     (results tagged with session ID)
                        ├── S3           (results storage)
                        └── CloudWatch EMF → Grafana
```

Each worker task is an independent agent session. The task ARN — injected by ECS at runtime — serves as the session identity, so you can always trace which container handled which request.

## Prerequisites

To follow along you will need:

- An AWS account with permissions to create ECS, DynamoDB, SQS, S3, IAM, and CloudWatch resources
- AWS CDK installed (`npm install -g aws-cdk`) and bootstrapped in your account
- Docker installed and running
- Node.js 18+ and Python 3.12+
- A GitHub repository with OIDC configured for deployments
- An Anthropic API key stored in AWS Secrets Manager

---

## The Infrastructure: One CDK Stack

All infrastructure lives in `infra/` as TypeScript CDK in a single stack: `LoadTestStack`. I went with one stack deliberately to avoid the cross-stack export deadlocks that bite you when resources in separate stacks have circular dependencies. Everything deploys together, so you never have to reason about deploy order.

### Foundation: Networking, Storage, and Queues

`LoadTestStack` creates the VPC, ECR repositories, DynamoDB table, SQS queues, S3 results bucket, and IAM task roles.

The DynamoDB table (`queue-jobs`) uses `jobId` as the partition key and `createdAt` as the sort key, with a GSI on `status` so you can query all running jobs without a full table scan.

```typescript
const table = new dynamodb.Table(this, 'JobsTable', {
  tableName: 'queue-jobs',
  partitionKey: { name: 'jobId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'createdAt', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  pointInTimeRecovery: true,
});

table.addGlobalSecondaryIndex({
  indexName: 'status-index',
  partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'createdAt', type: dynamodb.AttributeType.STRING },
});
```

There are two SQS queues. `loadtest-jobs` carries job metadata, and `loadtest-target` is the agent request queue — one message per user request. The work queue has a 30-second visibility timeout, long enough for a worker to start processing before another worker could claim the same message. A dead-letter queue with `maxReceiveCount: 3` catches requests that fail repeatedly rather than letting them cycle forever.

For IAM, two task roles with least-privilege policies. `ControlPlaneTaskRole` can write to DynamoDB and send to `loadtest-target`. `WorkerTaskRole` can read from `loadtest-target`, write to DynamoDB and S3, publish CloudWatch metrics, and read secrets from Secrets Manager. Neither has anything broader than it needs.

### The Control Plane: FastAPI on Fargate

The control plane is a FastAPI app running as a Fargate task behind an Application Load Balancer.

```typescript
const service = new ecs.FargateService(this, 'ControlPlaneService', {
  cluster,
  taskDefinition,
  desiredCount: 0,  // pipeline scales this up after deploy
  assignPublicIp: false,
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
});
```

Notice `desiredCount: 0` — the CDK stack always deploys with services stopped. The CI/CD pipeline scales them up after the deploy succeeds, which means CloudFormation never tries to pull a container image that does not exist yet. It is a simple trick that eliminates an entire class of first-deploy failures.

On `POST /jobs`, the API generates a ULID for the job (ULIDs are lexicographically sortable unlike UUIDs, which makes range queries on DynamoDB cleaner), writes a `PENDING` record to DynamoDB, puts the request on `loadtest-target`, and marks it `RUNNING`.

```python
@router.post("/jobs", status_code=202, response_model=JobResponse)
async def create_job(body: CreateJobRequest):
    job_id = str(ULID())
    await dynamodb_client.put_item(job_id, status="PENDING", config=body.model_dump())
    await sqs_client.send_messages(job_id, body.messageCount, body.processingTime)
    await dynamodb_client.update_status(job_id, "RUNNING", startedAt=now())
    return JobResponse(jobId=job_id, status="RUNNING")
```

The full API surface is:

- `POST /jobs` — submit a new agent job
- `GET /jobs/{jobId}` — check status and get results
- `GET /jobs` — list all jobs, optionally filtered by `?status=RUNNING`
- `DELETE /jobs/{jobId}` — cancel a pending or running job

### The Worker: Session Identity + Agent

The worker is where the agent runs. Each task polls SQS, picks up a request, processes it, and writes results back — tagged with a session ID that identifies exactly which container did the work.

The service starts at `desiredCount: 0`. Autoscaling handles everything from there.

The first thing the worker does on startup is resolve its own session identity. ECS injects a metadata URI into every task at runtime — the worker calls it to get its task ARN, which becomes the session ID attached to everything that container produces.

```python
def get_session_id() -> str:
    metadata_uri = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
    if not metadata_uri:
        return f"local-{uuid.uuid4()}"  # fallback for local dev
    response = urllib.request.urlopen(f"{metadata_uri}/task", timeout=3)
    task_metadata = json.loads(response.read())
    # arn:aws:ecs:us-east-1:123456789:task/cluster/abc123 → abc123
    return task_metadata["TaskARN"].split("/")[-1]

SESSION_ID = get_session_id()
```

And just like that, every container knows who it is. The main processing loop:

```python
claude_client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

while True:
    message = sqs.receive_message(WaitTimeSeconds=20, VisibilityTimeout=60)
    if not message:
        empty_polls += 1
        if empty_polls >= MAX_EMPTY_POLLS:  # ~60s idle before exit
            break
        continue

    job_id, receipt_handle, payload = parse(message)
    set_scale_in_protection(enabled=True)

    response = claude_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": payload["prompt"]}],
    )

    # every result is tagged with this session's identity
    write_result(job_id, SESSION_ID, response.content[0].text)
    metrics_emitter.emit(job_id, SESSION_ID, elapsed_ms)

    sqs.delete_message(receipt_handle)
    set_scale_in_protection(enabled=False)
```

Everything written back — the DynamoDB result, the S3 object, the CloudWatch metric — carries the `SESSION_ID`. When you look at Grafana or query DynamoDB, you can see exactly which container handled which request, how long it took, and what it returned.

The scale-in protection calls are important. Before the Claude API call, the worker tells the ECS agent it is busy. This prevents the autoscaler from terminating a session mid-request. After the message is deleted and results are written, protection is disabled and ECS is free to scale down if needed.

Workers process multiple requests per container and only exit after 3 consecutive empty polls (~60 seconds idle). This keeps compute costs reasonable compared to spinning up a fresh container per request.

### Autoscaling: Target Tracking on Queue Depth

The autoscaling uses target tracking on a custom metric — backlog per running worker — rather than step scaling on raw queue depth.

The idea: if there are 1,000 pending requests and 2 workers running, each worker has 500 to handle. If the target is 500 messages per task, the policy is satisfied. Submit another 1,000 requests and the policy scales to 4 workers to bring each one's share back to 500.

```typescript
new appscaling.CfnScalingPolicy(this, 'WorkerBacklogTrackingPolicy', {
  policyType: 'TargetTrackingScaling',
  targetTrackingScalingPolicyConfiguration: {
    targetValue: 500,       // 500 requests per running worker
    scaleOutCooldown: 60,   // react fast to new jobs
    scaleInCooldown: 300,   // be conservative scaling in
    customizedMetricSpecification: {
      metrics: [
        { id: 'm1', /* ApproximateNumberOfMessagesVisible on loadtest-target */ },
        { id: 'm2', /* ECS RunningTaskCount from Container Insights */ },
        {
          id: 'e1',
          expression: 'IF(m2 > 0, m1 / m2, m1)',  // backlog per worker
          returnData: true,
        },
      ],
    },
  },
});
```

There is one wrinkle: when the service is at zero workers, Container Insights has no `RunningTaskCount` data point, so the target tracking expression cannot evaluate. A bootstrap alarm handles this — it fires when queue depth hits 1 and immediately sets desired count to 1. Once that first worker is running, Container Insights starts publishing and target tracking takes over from there.

```typescript
const bootstrapAlarm = new cloudwatch.Alarm(this, 'QueueDepthAlarm', {
  metric: targetQueue.metricApproximateNumberOfMessagesVisible(),
  threshold: 1,
  evaluationPeriods: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
});
// alarm action sets exact capacity to 1
```

---

## Metrics: CloudWatch EMF

The worker uses Embedded Metric Format to emit structured metrics as JSON to stdout. CloudWatch Logs picks them up automatically — no extra API calls, no metric clients.

```python
def emit(job_id, session_id, elapsed_ms):
    print(json.dumps({
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": "QueueScaling",
                "Dimensions": [["jobId", "sessionId"]],
                "Metrics": [
                    {"Name": "totalProcessed", "Unit": "Count"},
                    {"Name": "avgProcessingMs", "Unit": "Milliseconds"},
                ],
            }]
        },
        "jobId": job_id,
        "sessionId": session_id,
        "totalProcessed": 1,
        "avgProcessingMs": elapsed_ms,
    }), flush=True)
```

Dimensioning on both `jobId` and `sessionId` means you can slice metrics by job (how did this batch perform overall?) or by individual session (did one particular worker run slower than the others?). This is how you spot things like one container hitting an API rate limit while the rest are fine.

---

## Grafana: Pre-Provisioned Dashboards

Grafana runs as its own Fargate service with a custom Docker image that bakes in the CloudWatch datasource and a pre-built dashboard. When the container starts, everything is already configured.

```yaml
# provisioning/datasources/cloudwatch.yaml
apiVersion: 1
datasources:
  - name: CloudWatch
    type: cloudwatch
    uid: cloudwatch
    isDefault: true
    jsonData:
      authType: default
      defaultRegion: ${AWS_REGION}
```

`authType: default` means Grafana authenticates to CloudWatch using the ECS task role. No access keys, no secrets in environment variables. The admin password is stored in Secrets Manager and injected at runtime — no hardcoded credentials anywhere.

Submit a job, open Grafana when it finishes. You will see queue depth, running worker count, DLQ depth, and per-job and per-session metrics side by side. If one session took significantly longer than the others, you can see it immediately.

And just like that, you have a production-grade observability layer with zero Grafana configuration on first deploy.

---

## CI/CD: GitHub Actions with OIDC

The deployment pipeline builds and pushes Docker images to ECR, then deploys the CDK stack. Authentication uses OIDC — no long-lived AWS access keys stored as GitHub secrets.

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsDeployRole
    aws-region: us-east-1
    role-duration-seconds: 14400
```

The pipeline detects which services changed using `git diff` and only rebuilds affected images. Images are tagged with the commit SHA and `latest`.

```yaml
- name: Deploy stack
  run: |
    npx cdk deploy LoadTestStack \
      --context controlPlaneTag=$CP_TAG \
      --context workerTag=$WORKER_TAG \
      --context grafanaTag=$GRAFANA_TAG \
      --require-approval never

- name: Scale up services
  run: |
    aws ecs update-service --cluster $CLUSTER --service $CP_SERVICE \
      --desired-count 1 --region us-east-1
    aws ecs update-service --cluster $CLUSTER --service $GRAFANA_SERVICE \
      --desired-count 1 --region us-east-1
```

Workers stay at zero and are managed entirely by the autoscaling policy. Deploy only runs on pushes to `main`. On every PR, the CI workflow runs pytest and CDK assertion tests without pushing any images.

---

## Running a Job

Once deployed, submitting a batch of agent requests is one command:

```bash
curl -X POST http://<alb-dns>/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent-batch",
    "messageCount": 500,
    "processingTime": 500
  }'
```

You get back a `jobId`. Poll `GET /jobs/{jobId}` to watch the status. Within about 60 to 90 seconds workers are up and running agent sessions. When the job finishes, check the Grafana dashboard for results broken down by job and by session.

---

## A Few Things Worth Knowing

The 60 to 90 second cold start is the main trade-off with this design. One CloudWatch evaluation period plus Fargate cold start time. For agent workloads where sessions run for more than a few seconds, it is acceptable. If you need near-instant startup, you would need warm workers, which changes the cost profile.

Workers exit after 3 consecutive empty polls (~60 seconds idle). Tune `MAX_EMPTY_POLLS` based on your traffic patterns — if you have bursty workloads with short gaps between batches, raising it avoids unnecessary scale-in and cold starts.

The bootstrap alarm and target tracking policy do different jobs. Do not remove the alarm thinking target tracking handles zero-to-one — it does not, because the metric expression needs at least one running worker to evaluate.

---

## The Repo

The full project is on GitHub at [ajaydhungel7/queue-based-autoscaling](https://github.com/ajaydhungel7/queue-based-autoscaling). The README covers CDK bootstrap, deployment order, and how to wire up the GitHub OIDC role.

If you are running AI agent workloads on AWS and want elastic, zero-idle infrastructure where every session is traceable, this is a solid starting point.

---

That's all for now! Thank you so much for making it to the end.
