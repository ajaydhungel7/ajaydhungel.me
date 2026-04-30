---
title: "One Command to a Running Cluster: Terraform, ArgoCD, and the GitOps Handoff"
date: 2026-04-30
draft: false
author: Ajay Dhungel
description: "How I use Terraform to provision EKS and hand off to ArgoCD, so the entire platform self-assembles from a single command."
tags: ["kubernetes", "terraform", "argocd", "aws", "devops", "gitops", "eks"]
tech: ["kubernetes", "terraform", "aws", "github-actions"]
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Introduction

There is a question that comes up every time you start using both Terraform and Kubernetes: where does Terraform stop and something else begin?

The naive answer is to let Terraform manage everything. It can install Helm charts, create Kubernetes resources, manage namespaces. But there is a fundamental problem with that approach. Terraform tracks state as a snapshot. It knows what it deployed, but it has no idea what is actually running. If a deployment crashes, if pods are stuck in pending, if someone deletes something manually -- Terraform does not know and does not care. It will report everything as fine because its state file says so.

ArgoCD was built for exactly the problem Terraform cannot solve: continuous reconciliation. It watches your cluster against a desired state in Git and keeps them in sync, forever. If something drifts, ArgoCD fixes it. If a pod crashes, ArgoCD reconciles. Terraform cannot do that.

So the right split is straightforward. Terraform provisions the infrastructure -- the cluster, the networking, the IAM roles, the secrets. ArgoCD manages everything inside the cluster. The question is just how you connect the two cleanly.

---

## What Terraform Owns

Terraform handles everything that lives outside the cluster or is needed to bring the cluster into existence:

- **VPC** -- subnets, NAT gateway, internet gateway, route tables
- **EKS cluster** -- control plane, node groups, OIDC provider
- **IAM roles** -- one per controller, all using IRSA so no static credentials ever touch the cluster
- **KMS key and Secrets Manager entries** -- encrypted at rest, path-namespaced per environment
- **ECR repositories** -- with lifecycle policies so old images do not accumulate
- **ArgoCD** -- installed via a single `helm_release`, this is where Terraform stops

That last point is important. Terraform installs ArgoCD, and that is the last thing it does inside the cluster. Everything that comes after -- controllers, drivers, application workloads -- is ArgoCD's responsibility.

---

## Why Terraform Stops at ArgoCD

When Terraform runs a `helm_release`, it marks the resource as complete as soon as the chart is installed. It does not wait for pods to be ready, does not check if the deployment is healthy, and has no way to know if the application is actually running. From Terraform's perspective, installed and running are the same thing.

More importantly, Terraform has no reconciliation loop. It applies once and moves on. If a controller crashes an hour later, Terraform will not notice. If someone edits a ConfigMap manually, Terraform will not revert it. Drift is invisible to Terraform unless you run a plan again.

ArgoCD does the opposite. It runs a continuous loop comparing what is in Git to what is in the cluster. Any difference gets corrected automatically. That is the behaviour you want for everything running inside Kubernetes.

So the split is: Terraform for infrastructure that needs to exist before the cluster is useful, ArgoCD for everything that runs inside it.

---

## The Handoff

The EKS Addons module is where the handoff happens. It does two things: installs ArgoCD via Helm, then waits for ArgoCD to be ready and applies the root application.

```hcl
resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  namespace        = "argocd"
  create_namespace = true
}

resource "null_resource" "argocd_root_app" {
  depends_on = [helm_release.argocd]

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      echo "Waiting for ArgoCD server to be ready..."
      kubectl wait deployment/argocd-server \
        --for=condition=available \
        --namespace=argocd \
        --timeout=180s \
        --server="${var.cluster_endpoint}" \
        --certificate-authority=<(echo "${var.cluster_ca_certificate}" | base64 -d) \
        --token="${data.aws_eks_cluster_auth.main.token}"

      echo "Applying root ArgoCD application for environment: ${var.environment}"
      kubectl apply \
        -f "${var.repo_root}/argocd/bootstrap/root-app-${var.environment}.yaml" \
        --server="${var.cluster_endpoint}" \
        --certificate-authority=<(echo "${var.cluster_ca_certificate}" | base64 -d) \
        --token="${data.aws_eks_cluster_auth.main.token}"
    EOT
  }
}
```

The `depends_on` ensures the `local-exec` only runs after the Helm release is complete. The `kubectl wait` then blocks until the `argocd-server` deployment is actually available, not just installed. Only then does it apply the root app. This is the part that was previously a manual step -- you had to run the `kubectl apply` yourself after Terraform finished. Now it happens automatically as part of the same apply.

---

## The Root App

The root application is a single ArgoCD Application manifest that points at the `argocd/apps` directory in the repo:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: k8s-gitops-root-dev
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/ajaydhungel7/k8s-gitops
    targetRevision: dev
    path: argocd/apps
    helm:
      valueFiles:
        - values.yaml
        - values-dev.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

When this gets applied, ArgoCD reads the `argocd/apps` Helm chart, renders `values-dev.yaml` into a set of Application CRDs, and starts syncing all of them. This is the App of Apps pattern -- one root app that generates all other apps.

---

## App of Apps: values-dev.yaml as the Source of Truth

The `argocd/apps` directory is a Helm chart with a template that generates ArgoCD Application CRDs from a values file. Everything ArgoCD deploys in the dev environment is declared in `values-dev.yaml`.

It is split into two lists:

**Platform applications** -- system-level components the cluster needs to function:

```yaml
platformApplications:
  - name: aws-ebs-csi-driver
    namespace: kube-system
    syncWave: "-20"
    source:
      repoURL: https://kubernetes-sigs.github.io/aws-ebs-csi-driver
      chart: aws-ebs-csi-driver
      targetRevision: 2.x.x

  - name: aws-load-balancer-controller
    namespace: kube-system
    syncWave: "-20"
    source:
      repoURL: https://aws.github.io/eks-charts
      chart: aws-load-balancer-controller
      targetRevision: 1.11.0

  - name: cluster-autoscaler
    namespace: kube-system
    syncWave: "-20"

  - name: external-secrets
    namespace: external-secrets
    syncWave: "-10"

  - name: configs
    syncWave: "-5"

  - name: jenkins
    syncWave: "0"
```

**Workload applications** -- the actual services:

```yaml
workloadApplications:
  - name: mongodb
    syncWave: "5"
  - name: redis
    syncWave: "5"
  - name: backend
    syncWave: "10"
  - name: frontend
    syncWave: "10"
```

To add a new component to the cluster, you add an entry to this file and push. ArgoCD picks it up and deploys it. To remove something, you delete the entry. ArgoCD prunes it. The file is the complete description of what should be running.

---

## Sync Waves: Why Order Matters

ArgoCD does not deploy everything at once. Sync waves control the order, and getting the order wrong causes failures. Here is why each wave is where it is:

| Wave | What deploys | Why first |
|---|---|---|
| -20 | EBS CSI, ALB Controller, Cluster Autoscaler, Metrics Server | Storage and networking primitives. Everything else depends on these. |
| -10 | External Secrets Operator | Must be running before any app tries to pull a secret |
| -5 | Configs (StorageClass, ClusterSecretStore, namespaces) | ClusterSecretStore must exist before ExternalSecret resources are created |
| 0 | Jenkins | CI tooling, independent of workloads |
| 5 | MongoDB, Redis | Databases must be up before the apps that use them |
| 10 | Backend, Frontend | Last to deploy, all dependencies are ready |

If you skip the waves and deploy everything simultaneously, ExternalSecret resources will fail because ESO is not running yet, apps will fail because the database is not ready, and the ALB controller will not exist to reconcile Ingress resources. Waves are not optional.

---

## IRSA: How Controllers Get AWS Permissions

Every controller that needs to talk to AWS -- EBS CSI to provision volumes, ALB Controller to manage load balancers, External Secrets to read from Secrets Manager -- needs an IAM role. But those roles are created by Terraform, not ArgoCD.

The connection between them is the service account annotation. Terraform creates an IAM role with a trust policy scoped to a specific Kubernetes service account:

```hcl
condition {
  test     = "StringEquals"
  variable = "${local.oidc_host}:sub"
  values   = ["system:serviceaccount:kube-system:ebs-csi-controller-sa"]
}
```

ArgoCD then deploys the controller with that annotation on the service account:

```yaml
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/k8s-gitops-dev-ebs-csi-role
```

When the pod starts, the EKS pod identity agent sees the annotation, validates the service account against the OIDC provider, and injects temporary AWS credentials. No static keys, no secrets to rotate, no credentials stored anywhere.

Terraform creates the roles. ArgoCD annotates the service accounts. Neither needs to know the details of the other.

---

## Secrets: From AWS to the Pod

The secrets flow follows a similar pattern. Terraform creates the KMS key and the Secrets Manager entries. It never puts credentials in Kubernetes directly.

External Secrets Operator, deployed by ArgoCD, holds an IRSA role that allows it to read from Secrets Manager. A `ClusterSecretStore` resource points ESO at the right AWS region and account. Then `ExternalSecret` resources in each namespace declare which secrets to pull and what to name them as Kubernetes Secrets.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: backend-secrets
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  data:
    - secretKey: MONGODB_PASSWORD
      remoteRef:
        key: /k8s-gitops/dev/mongodb/credentials
        property: password
```

The pod mounts the resulting Kubernetes Secret as an environment variable. At no point does a credential appear in Git, in a values file, or in Terraform state.

---

## What Happens After One Command

Once `terragrunt run --all apply` finishes, this is what has happened without any further manual steps:

1. VPC, subnets, and networking are provisioned
2. EKS cluster and node group are running
3. OIDC provider is attached to the cluster
4. IAM roles for all controllers are created
5. KMS key and Secrets Manager entries exist
6. ECR repositories are ready
7. ArgoCD is installed and the server is healthy
8. The root app is applied
9. ArgoCD reads `values-dev.yaml` and generates all Application CRDs
10. Platform controllers install in wave -20: EBS CSI, ALB Controller, Cluster Autoscaler, Metrics Server
11. External Secrets Operator installs in wave -10
12. ClusterSecretStore and namespaces are created in wave -5
13. Jenkins installs in wave 0
14. MongoDB and Redis start in wave 5, pulling credentials from Secrets Manager via ESO
15. Backend and Frontend deploy in wave 10, connecting to the databases

The entire platform assembles itself. You run one command and walk away.

---

## Further Reading

- [ArgoCD documentation](https://argo-cd.readthedocs.io/)
- [App of Apps pattern](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/)
- [ArgoCD sync waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [IRSA on EKS](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [External Secrets Operator](https://external-secrets.io/)
