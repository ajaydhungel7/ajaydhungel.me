---
title: "How I Structure My Terragrunt Setup"
date: 2026-04-29
draft: false
author: Ajay Dhungel
description: "A walkthrough of how I structure Terragrunt for real projects, covering bootstrapping with CloudFormation, remote state, environment configs, and dependency chaining."
tags: ["terraform", "terragrunt", "aws", "devops", "iac", "github-actions"]
tech: ["terraform", "terragrunt", "aws", "github-actions", "iac"]
cover:
  image: /imgs/post-002.png
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Introduction

Terraform gets messy fast. A single `main.tf` works fine for a few resources. The moment you have multiple components that depend on each other, multiple environments, and a team sharing state, things start to break down.

Terragrunt is a thin wrapper around Terraform that solves three specific problems: keeping your configuration DRY, managing remote state without repeating backend blocks everywhere, and wiring up dependencies between components so they share outputs cleanly.

This is how I structure it on real projects.

---

## Bootstrapping with CloudFormation

Before Terragrunt can manage state, you need somewhere to put that state. This is the chicken-and-egg problem: you need infrastructure to run Terraform, but Terraform manages your infrastructure.

I solve this with a CloudFormation template. CloudFormation is the right tool here because it is AWS-native, requires no local state, and can be deployed with a single CLI command before anything else exists. The template creates three things:

1. An S3 bucket for Terraform state, with versioning, encryption, and public access blocked
2. A GitHub Actions OIDC provider so your pipeline can authenticate to AWS without storing any credentials
3. An IAM role that GitHub Actions assumes via that OIDC provider, with the permissions needed to run Terragrunt

```bash
aws cloudformation deploy \
  --template-file bootstrap/bootstrap.yml \
  --stack-name k8s-gitops-bootstrap \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=k8s-gitops \
    GitHubOrg=ajaydhungel7 \
    GitHubRepo=k8s-gitops \
    GitHubBranch=main
```

That is the only manual step in the entire setup. After this runs, the stack outputs the S3 bucket name and the IAM role ARN. Everything else is automated.

### Why OIDC instead of access keys

The OIDC approach means GitHub Actions never holds a long-lived AWS credential. Instead, when a workflow runs, GitHub mints a short-lived token scoped to that specific repo and branch. AWS verifies the token against the OIDC provider and issues temporary credentials.

The trust policy on the IAM role controls exactly which repo and branch can assume it:

```yaml
Condition:
  StringEquals:
    token.actions.githubusercontent.com:aud: sts.amazonaws.com
  StringLike:
    token.actions.githubusercontent.com:sub: "repo:ajaydhungel7/k8s-gitops:ref:refs/heads/main"
```

Nothing can assume this role except a GitHub Actions run on `main` in that specific repo. No key rotation, no secrets to manage, no risk of a leaked credential.

In your GitHub Actions workflow, you reference the role ARN from the CloudFormation output:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/k8s-gitops-github-actions
    aws-region: us-east-1
```

---

## The Folder Structure

Once bootstrapping is done, all infrastructure lives under `terraform/` with a clean split between live configs and reusable modules:

```
terraform/
├── root.hcl                      # Global config: remote state, project name, region
├── bootstrap/
│   └── bootstrap.yml             # CloudFormation template, run once manually
├── environments/
│   └── dev/
│       ├── env.hcl               # Dev-specific variables
│       ├── vpc/
│       │   └── terragrunt.hcl
│       ├── secrets/
│       │   └── terragrunt.hcl
│       ├── eks-cluster/
│       │   └── terragrunt.hcl
│       ├── eks-addons/
│       │   └── terragrunt.hcl
│       ├── iam/
│       │   └── terragrunt.hcl
│       └── ecr/
│           └── terragrunt.hcl
└── modules/
    ├── vpc/
    ├── eks-cluster/
    ├── eks-addons/
    ├── iam/
    ├── secrets/
    └── ecr/
```

`environments/` is where Terragrunt lives. Each subfolder is one deployable component with its own state file. `modules/` is plain Terraform, reusable code with no Terragrunt in it. The two are intentionally separate.

---

## The Root Config

`root.hcl` sits at the top of `terraform/` and is included by every component. It handles remote state configuration once, for everything.

```hcl
locals {
  path_parts = split("/", path_relative_to_include())
  env        = local.path_parts[1]
  region     = "us-east-1"
  project    = "k8s-gitops"
}

remote_state {
  backend = "s3"

  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }

  config = {
    bucket       = "k8s-gitops-terraform-state"
    key          = "${path_relative_to_include()}/terraform.tfstate"
    region       = local.region
    encrypt      = true
    use_lockfile = true
  }
}
```

Two things worth calling out here.

The `generate` block auto-creates a `backend.tf` file in each component directory at plan/apply time. You never write a backend block in any module. The root config handles it for everyone.

The state key uses `path_relative_to_include()`, which returns the path from the root to the current component. For `environments/dev/vpc`, the key becomes `environments/dev/vpc/terraform.tfstate`. Every component gets its own isolated state file without any manual configuration.

The `env` local is parsed directly from the path: `path_parts[1]` is `dev` when you are inside `environments/dev/`. When you add a `staging` or `prod` folder later, it picks up automatically.

---

## Environment Config

Each environment has an `env.hcl` that holds values specific to that environment: network ranges, node sizes, anything that differs between dev and prod.

```hcl
# environments/dev/env.hcl
locals {
  vpc_cidr         = "10.0.0.0/16"
  public_subnets   = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets  = ["10.0.10.0/24", "10.0.11.0/24"]
  azs              = ["us-east-1a", "us-east-1b"]

  node_instance_type = "t3.medium"
  node_min_size      = 1
  node_max_size      = 3
  node_desired_size  = 2
}
```

Components read this file using `read_terragrunt_config`:

```hcl
locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))
}
```

Then reference values as `local.env_vars.locals.vpc_cidr`. There are no `.tfvars` files anywhere in this setup. All configuration is in `.hcl` files, which keeps everything in one place and makes it obvious what changes between environments.

---

## A Component Config

Every component follows the same pattern. Here is what one looks like:

```hcl
locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))
}

include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "../../../modules/vpc"
}

inputs = {
  project     = include.root.locals.project
  environment = include.root.locals.env

  vpc_cidr             = local.env_vars.locals.vpc_cidr
  public_subnet_cidrs  = local.env_vars.locals.public_subnets
  private_subnet_cidrs = local.env_vars.locals.private_subnets
  availability_zones   = local.env_vars.locals.azs

  tags = {
    Project     = include.root.locals.project
    Environment = include.root.locals.env
    ManagedBy   = "terraform"
  }
}
```

The `include "root"` block pulls in remote state and exposes the locals from `root.hcl`. The `expose = true` is what lets you reference `include.root.locals.project` directly in inputs. The `terraform.source` points at the module. The `inputs` block passes everything down.

That is the full pattern. Every component in `environments/dev/` looks like this.

---

## Dependency Chaining

This is where Terragrunt saves the most time. Components share outputs with each other through `dependency` blocks instead of data sources or hardcoded values.

```hcl
dependency "vpc" {
  config_path = "../vpc"

  mock_outputs = {
    public_subnet_ids  = ["subnet-mock1", "subnet-mock2"]
    private_subnet_ids = ["subnet-mock3", "subnet-mock4"]
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan"]
}

inputs = {
  public_subnet_ids  = dependency.vpc.outputs.public_subnet_ids
  private_subnet_ids = dependency.vpc.outputs.private_subnet_ids
}
```

Terragrunt reads the remote state of the VPC component and injects its outputs directly as inputs to the EKS component. No data sources, no manual copying of IDs.

The mock outputs are important. When you run `terragrunt plan` on a component before its dependencies are deployed, Terragrunt uses the mock values instead of failing. This lets you validate configs and run CI checks without having real infrastructure in place.

A component can have multiple dependencies. The IAM component depends on both the EKS cluster (for the OIDC provider ARN) and the secrets component (for the KMS key ARN):

```hcl
dependency "eks_cluster" {
  config_path = "../eks-cluster"
  mock_outputs = {
    oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/MOCK"
    oidc_provider_url = "oidc.eks.us-east-1.amazonaws.com/id/MOCK"
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan"]
}

dependency "secrets" {
  config_path = "../secrets"
  mock_outputs = {
    kms_key_arn = "arn:aws:kms:us-east-1:123456789012:key/mock-key-id"
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan"]
}
```

---

## Deployment Order

The dependency declarations form a graph. Terragrunt resolves it automatically when you run:

```bash
terragrunt run-all apply
```

From the `dev/` folder, it figures out the order itself:

```
secrets ──────────────────────┐
                              ▼
vpc ──────────> eks-cluster ──> iam
                    │
                    ▼
              eks-addons

ecr  (independent, runs in parallel)
```

Components with no dependencies run first, in parallel if possible. Components with dependencies wait for their dependencies to complete. You do not have to think about order.

You can also target a single component:

```bash
cd environments/dev/eks-cluster
terragrunt apply
```

Terragrunt applies only that component, but resolves dependency outputs from existing state automatically.

---

## Adding a New Environment

To add `staging`, copy the `dev/` folder, rename it, and update `env.hcl` with staging values: larger nodes, different CIDR ranges, whatever is appropriate.

```
environments/
├── dev/
│   └── env.hcl   # t3.medium, min 1 node
└── staging/
    └── env.hcl   # t3.large, min 2 nodes
```

The `root.hcl` picks up `staging` automatically from the path. State files land under `environments/staging/` in S3. No other files need to change.

The first environment takes time to set up properly. Every environment after that is a folder copy and a few variable changes.

---

## Further Reading

- [Terragrunt documentation](https://terragrunt.gruntwork.io/docs/)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [Terraform S3 native state locking](https://developer.hashicorp.com/terraform/language/backend/s3)
