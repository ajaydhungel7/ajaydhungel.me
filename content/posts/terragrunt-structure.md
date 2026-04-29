---
title: "How I Structure My Terragrunt Setup for Kubernetes Infrastructure"
date: 2026-04-29
draft: false
author: Ajay Dhungel
description: "A walkthrough of how I structure Terragrunt for a real Kubernetes project, covering remote state, dependency chaining, env configs, and IRSA patterns."
tags: ["terraform", "terragrunt", "kubernetes", "aws", "devops", "iac"]
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Introduction

There are a lot of tutorials on Terraform. There are fewer on how to actually organize it when things get real. Once you have more than a handful of resources, a single `main.tf` becomes a liability. Once you have more than one environment, copying folders around becomes a nightmare.

Terragrunt solves both problems. It is a thin wrapper around Terraform that adds DRY configuration, remote state management, and dependency tracking without changing how Terraform itself works.

This is how I structure it for a real Kubernetes project on AWS, including VPC, EKS, IAM with IRSA, secrets, and container registries.

---

## The Folder Structure

Everything lives under a `terraform/` directory at the root of the project. The split is straightforward: `environments/` holds the live Terragrunt configs per environment, and `modules/` holds the reusable Terraform code.

```
terraform/
├── root.hcl                        # Global config: remote state, project, region
├── bootstrap/                      # One-time AWS account setup
│   ├── main.tf
│   ├── outputs.tf
│   └── variables.tf
├── environments/
│   └── dev/
│       ├── env.hcl                 # Dev-specific variables
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

Each component under `environments/dev/` gets its own folder with a single `terragrunt.hcl`. Each folder corresponds to one module in `modules/`. The state file for each component is stored separately in S3, which means you can plan and apply them independently.

---

## The Root Config

The `root.hcl` file sits at the top of the `terraform/` directory and handles two things: extracting globals from the directory path and configuring remote state for every component automatically.

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

The `path_relative_to_include()` function returns the path from the root to the current component, like `environments/dev/vpc`. That becomes the S3 key, so each component gets its own state file:

```
k8s-gitops-terraform-state/
  environments/dev/vpc/terraform.tfstate
  environments/dev/eks-cluster/terraform.tfstate
  environments/dev/iam/terraform.tfstate
  ...
```

The `generate` block auto-creates a `backend.tf` file in each component directory at runtime. You never have to write backend configuration by hand in any module. Every child that includes `root.hcl` gets remote state for free.

The `env` local parses the environment name directly from the directory path. When you are inside `environments/dev/vpc`, `path_parts[1]` is `dev`. Add a `staging` or `prod` folder later and it picks up automatically.

---

## Environment Variables

Each environment has an `env.hcl` file that holds the values specific to that environment: networking config, node sizing, anything that changes between dev and prod.

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

Components that need these values read them with `read_terragrunt_config`:

```hcl
locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))
}
```

Then reference them as `local.env_vars.locals.vpc_cidr`. There are no `.tfvars` files anywhere in this setup. All configuration flows through `.hcl` files, which means it is all in one place and you can see exactly what each environment uses without hunting around.

---

## A Component Config

Here is the VPC component as an example of what every `terragrunt.hcl` looks like:

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

Three things are happening here. The `include "root"` block pulls in remote state config and exposes the locals so you can reference `include.root.locals.project`. The `terraform.source` points at the module. The `inputs` block passes everything the module needs. That is the full pattern for every component.

---

## Dependency Chaining

This is where Terragrunt really earns its place. The EKS cluster needs subnet IDs from the VPC. Instead of hardcoding them or using data sources, you declare a dependency:

```hcl
dependency "vpc" {
  config_path = "../vpc"

  mock_outputs = {
    public_subnet_ids  = ["subnet-mock1", "subnet-mock2"]
    private_subnet_ids = ["subnet-mock3", "subnet-mock4"]
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan"]
}
```

Then use the output directly as an input:

```hcl
inputs = {
  public_subnet_ids  = dependency.vpc.outputs.public_subnet_ids
  private_subnet_ids = dependency.vpc.outputs.private_subnet_ids
}
```

The mock outputs are what makes this practical. When you run `terragrunt plan` on the EKS cluster before the VPC is deployed, Terragrunt uses the mock values instead of failing. Real values are used when the VPC state actually exists. This means you can validate your configs and run CI checks before anything is provisioned.

The IAM component has two dependencies, which is a common pattern when a module needs outputs from multiple components:

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

## The Deployment Order

The dependency graph naturally defines the order components need to be deployed:

```
secrets ──────────────────────┐
                              ▼
vpc ──────────> eks-cluster ──> iam
                    │
                    ▼
              eks-addons

ecr  (independent)
```

1. **VPC** and **secrets** first, no dependencies
2. **EKS cluster** needs VPC subnets
3. **IAM** needs the OIDC provider from EKS and the KMS key from secrets
4. **EKS addons** needs the cluster endpoint and credentials
5. **ECR** is fully independent, can go any time

You can run `terragrunt run-all apply` from the `dev/` folder and Terragrunt figures out this order automatically from the dependency declarations.

---

## IRSA: IAM Roles for Service Accounts

The IAM module is worth calling out specifically because the pattern it implements, IRSA (IAM Roles for Service Accounts), is how you give Kubernetes workloads AWS permissions without managing static credentials.

The idea is that the EKS cluster has an OIDC provider attached to it. Each IAM role has a trust policy that allows a specific Kubernetes service account to assume it. That service account is then annotated in your workload, and AWS handles the credential exchange.

The IAM module creates five roles this way:

- **External Secrets Operator** -- reads from Secrets Manager and KMS, used to sync secrets into the cluster
- **Jenkins** -- ECR access and EKS describe, used by CI pipelines running inside the cluster
- **Cluster Autoscaler** -- reads and modifies Auto Scaling Groups to scale nodes
- **EBS CSI Driver** -- manages EBS volumes for persistent storage
- **AWS Load Balancer Controller** -- manages ALB and security groups for ingress

Each trust policy scope is tight. The External Secrets role can only be assumed by the `external-secrets` service account in the `external-secrets` namespace. Jenkins can only be assumed by the `jenkins` service account in the `jenkins` namespace. No service account can assume a role it was not explicitly granted.

This is what secure-by-design looks like in practice. No access keys, no shared credentials, no overly broad policies.

---

## Secrets

The secrets module creates two things:

- A KMS key with rotation enabled, aliased as `k8s-gitops-dev-secrets`
- Secrets Manager entries for database credentials, namespaced as `/{project}/{environment}/redis/password` and `/{project}/{environment}/mongodb/credentials`

The KMS key ARN is passed to the IAM module as a dependency output, so the External Secrets Operator role gets exactly the decrypt permission it needs for that specific key.

Inside the cluster, External Secrets Operator reads from Secrets Manager using its IRSA role and creates Kubernetes secrets. Application pods mount those secrets as environment variables or volumes. No secret ever lives in the codebase or in a `.tfvars` file.

---

## ECR Lifecycle Policies

ECR can fill up fast if you are not careful. The ECR module sets lifecycle policies on both repositories:

- Untagged images are deleted after 1 day
- Tagged images are kept up to 10, covering prefixes: `sha`, `dev`, `staging`, `prod`

This keeps storage costs down and ensures old images do not accumulate. The tagging convention also maps directly to the environments, so it is easy to trace which image is running where.

---

## Adding a New Environment

To add a `staging` environment, you copy the `dev/` folder, rename it to `staging/`, update `env.hcl` with staging-appropriate values (larger nodes, different CIDR ranges), and you are done. The `root.hcl` picks up `staging` automatically from the path. State files land in their own prefix in S3. No other files need to change.

That is the actual value of this structure. The first environment takes time to set up. Every environment after that is a folder copy and a few variable changes.

---

## Further Reading

- [Terragrunt documentation](https://terragrunt.gruntwork.io/docs/)
- [IRSA on EKS](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [External Secrets Operator](https://external-secrets.io/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
