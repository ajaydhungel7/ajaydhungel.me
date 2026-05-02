---
title: "One Command to a Running Cluster: Terraform, ArgoCD, and the GitOps Handoff"
date: 2026-04-30
draft: false
author: Ajay Dhungel
description: "How I use Terraform to provision EKS and hand off to ArgoCD, so the entire platform self-assembles from a single command."
tags: ["kubernetes", "terraform", "argocd", "aws", "devops", "gitops", "eks"]
tech: ["kubernetes", "terraform", "aws", "github-actions"]
cover:
  image: /imgs/terraform-argocd-cover.png
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Introduction

When I started using Terraform and Kubernetes together, one question kept coming up: where does Terraform stop and something else begin?

The easy answer is to let Terraform manage everything. It can install Helm charts, create Kubernetes resources, manage namespaces. But Terraform tracks state as a snapshot. It knows what it deployed, but has no idea what is actually running. If a deployment crashes, if pods are stuck pending, if someone deletes something manually, Terraform does not know and does not care. Its state file says everything is fine, so everything is fine.

ArgoCD was built for exactly that problem. It watches your cluster against a desired state in Git and keeps them in sync, continuously. If something drifts, ArgoCD fixes it. If a pod crashes, ArgoCD reconciles. Terraform will never do that.

So the split I landed on is this: Terraform provisions the infrastructure, ArgoCD manages everything inside the cluster. The interesting part is how you connect the two cleanly, and that is what this post is about.

---

## What Terraform Owns

Terraform handles everything that needs to exist before the cluster is useful:

- **VPC** -- subnets, NAT gateway, internet gateway, route tables
- **EKS cluster** -- control plane, node groups, OIDC provider
- **IAM roles** -- one per controller, all using IRSA so no static credentials ever touch the cluster
- **KMS key and Secrets Manager entries** -- encrypted at rest, path-namespaced per environment
- **ECR repositories** -- with lifecycle policies so old images do not accumulate
- **ArgoCD** -- installed via a single `helm_release`, and this is where Terraform stops

That last point matters. Terraform installs ArgoCD, and that is the last thing it does inside the cluster. Everything that comes after, controllers, drivers, application workloads, is ArgoCD's job.

---

## Why Terraform Stops at ArgoCD

When Terraform runs a `helm_release`, it marks the resource as complete as soon as the chart is installed. It does not wait for pods to be ready, does not check if the deployment is healthy, and genuinely cannot tell the difference between installed and running.

There is also no reconciliation loop. Terraform applies once and moves on. If a controller crashes an hour later, Terraform will not notice. If someone edits a ConfigMap manually, Terraform will not revert it. Drift is invisible unless you run a plan again.

ArgoCD runs a continuous loop comparing what is in Git to what is in the cluster, and corrects any difference automatically. That is the behaviour you want for everything running inside Kubernetes.

So: Terraform for the infrastructure that needs to exist, ArgoCD for everything that runs on top of it.

---

## Where Ansible Fits In

Before getting into the code, it is worth understanding why Ansible is involved at all.

Terraform finishes provisioning the EKS cluster and hands off to the next step. But at that point, the cluster exists and ArgoCD is installed via Helm, and that is all Terraform knows. It cannot tell you whether the ArgoCD pods are actually running, and it cannot apply Kubernetes manifests cleanly without reaching for raw `kubectl` in a `local-exec` block.

Raw `kubectl` in a shell script works, but it is fragile. You end up writing sleep commands, polling loops, and process substitution hacks just to pass a CA cert. It gets messy fast.

Ansible sits right in that gap. It has native Kubernetes modules that know how to wait for a deployment to become available without any of that. It speaks Terraform's language on one side -- it gets called from a `local-exec` and receives the cluster credentials as variables -- and it speaks Kubernetes on the other side, applying the root app manifest once the cluster is actually ready.

It is not doing anything magical. It is just the cleanest way to cross that boundary without turning the `local-exec` into a bash nightmare.

---

## The Handoff

The EKS Addons module is where the handoff happens. It installs ArgoCD via Helm, then once ArgoCD is ready, applies the root application that kicks everything else off.

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
      CA_CERT_FILE=$(mktemp /tmp/eks-ca-XXXXXX.crt)
      echo "${var.cluster_ca_certificate}" | base64 -d > "$CA_CERT_FILE"

      ansible-playbook "${var.repo_root}/ansible/argocd-bootstrap.yml" \
        -e "cluster_endpoint=${var.cluster_endpoint}" \
        -e "cluster_ca_cert_path=$CA_CERT_FILE" \
        -e "cluster_token=${data.aws_eks_cluster_auth.main.token}" \
        -e "env=${var.environment}"

      rm -f "$CA_CERT_FILE"
    EOT
  }
}
```

The `depends_on` ensures the `local-exec` only runs after the Helm release completes. I initially reached for raw `kubectl` commands here, but switched to an Ansible playbook. Ansible has proper Kubernetes modules that handle waiting for readiness natively, which is much cleaner than writing sleep loops in bash.

The CA cert gets written to a temp file because Ansible's Kubernetes modules expect a file path rather than a raw string. It gets cleaned up right after the playbook finishes.

### The Ansible Playbook

The playbook lives in `ansible/argocd-bootstrap.yml` and does two things: waits for the ArgoCD server to be healthy, then applies the root app manifest.

```yaml
- name: Bootstrap ArgoCD root application
  hosts: localhost
  connection: local
  gather_facts: false

  tasks:
    - name: Wait for ArgoCD server deployment to be available
      kubernetes.core.k8s_info:
        api_version: apps/v1
        kind: Deployment
        name: argocd-server
        namespace: argocd
        host: "{{ cluster_endpoint }}"
        ca_cert: "{{ cluster_ca_cert_path }}"
        api_key: "{{ cluster_token }}"
        wait: true
        wait_condition:
          type: Available
          status: "True"
        wait_timeout: 180

    - name: Apply ArgoCD root application
      kubernetes.core.k8s:
        state: present
        src: "{{ repo_root }}/argocd/bootstrap/root-app-{{ environment }}.yaml"
        host: "{{ cluster_endpoint }}"
        ca_cert: "{{ cluster_ca_cert_path }}"
        api_key: "{{ cluster_token }}"
```

The `k8s_info` module blocks until the `Available` condition is true or the timeout is hit. Only then does the `k8s` module apply the root app. No polling loops, no sleep commands, no guessing.

Before running, install the required collection:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

### How the Playbook Gets Cluster Permissions

The playbook runs on the same machine as Terraform, your laptop or the GitHub Actions runner. It does not use a kubeconfig file at all. The cluster endpoint, CA cert, and token are passed directly as extra vars.

The token comes from `data.aws_eks_cluster_auth`, which exchanges your current IAM identity for a short-lived Kubernetes bearer token. Whoever runs Terraform needs `eks:DescribeCluster` permission and needs to be authorized in the cluster's access entries. The GitHub Actions role created by the CloudFormation bootstrap already has both.

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

When this gets applied, ArgoCD reads the `argocd/apps` Helm chart, renders `values-dev.yaml` into a set of Application CRDs, and starts syncing all of them. This is the App of Apps pattern -- one root app that generates all the other apps.

---

## App of Apps: values-dev.yaml as the Source of Truth

The `argocd/apps` directory is a Helm chart whose single template generates ArgoCD Application CRDs from a values file. Everything ArgoCD deploys in the dev environment is declared in `values-dev.yaml`.

I split it into two lists. Platform applications are system-level components the cluster needs to function:

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

Workload applications are the actual services:

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

To add something new to the cluster, you add an entry here and push. ArgoCD picks it up and deploys it. To remove something, you delete the entry and ArgoCD prunes it. This file is the complete description of what should be running.

---

## How the Helm Template Generates Applications

The template in `argocd/apps` iterates over both lists and renders one ArgoCD Application CRD per entry:

```yaml
{{- $defaults := dict "project" .Values.project "destinationServer" .Values.destinationServer -}}
{{- $applications := concat .Values.platformApplications .Values.workloadApplications -}}
{{- range $app := $applications }}
{{- $spec := mergeOverwrite (deepCopy $defaults) $app -}}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {{ $spec.name }}
  namespace: argocd
  {{- if $spec.syncWave }}
  annotations:
    argocd.argoproj.io/sync-wave: {{ $spec.syncWave | quote }}
  {{- end }}
spec:
  project: {{ $spec.project }}
  source:
    {{- if $spec.source.repoURL }}
    repoURL: {{ $spec.source.repoURL }}
    {{- end }}
    {{- if $spec.source.chart }}
    chart: {{ $spec.source.chart }}
    {{- end }}
    {{- if $spec.source.path }}
    path: {{ $spec.source.path }}
    {{- end }}
    targetRevision: {{ default $.Values.targetRevision $spec.source.targetRevision }}
    {{- with $spec.source.helm }}
    helm:
      {{- with .releaseName }}
      releaseName: {{ . }}
      {{- end }}
      {{- with .valueFiles }}
      valueFiles:
        {{- range . }}
        - {{ . }}
        {{- end }}
      {{- end }}
      {{- with .values }}
      values: |
{{ . | indent 8 }}
      {{- end }}
    {{- end }}
  destination:
    server: {{ $spec.destinationServer }}
    namespace: {{ $spec.namespace }}
  syncPolicy:
    {{- if $spec.syncPolicy }}
{{ toYaml $spec.syncPolicy | indent 4 }}
    {{- end }}
    syncOptions:
      - CreateNamespace={{ ternary "true" "false" (default false $spec.createNamespace) }}
---
{{- end }}
```

The `mergeOverwrite` call merges each app entry on top of the shared defaults, so you only specify what is different per app. The `syncWave` annotation only renders if the field is set. The `ternary` on `CreateNamespace` lets you control namespace creation per app with a simple boolean rather than repeating the sync option everywhere.

When ArgoCD syncs the root app, it runs this template against `values-dev.yaml` and gets back a list of fully formed Application CRDs. Adding a new service to the cluster is just an entry in the values file and a push.

---

## Sync Waves: Why Order Matters

ArgoCD does not deploy everything at once. Sync waves control the order, and getting it wrong causes real failures. Here is how I have mine set up and why:

| Wave | What deploys | Why |
|---|---|---|
| -20 | EBS CSI, ALB Controller, Cluster Autoscaler, Metrics Server | Storage and networking primitives. Everything else depends on these. |
| -10 | External Secrets Operator | Must be running before any app tries to pull a secret. |
| -5 | Configs (StorageClass, ClusterSecretStore, namespaces) | ClusterSecretStore must exist before ExternalSecret resources are created. |
| 0 | Jenkins | CI tooling, independent of workloads. |
| 5 | MongoDB, Redis | Databases must be up before the apps that use them. |
| 10 | Backend, Frontend | Last to deploy, all dependencies are ready. |

If you skip the waves and deploy everything at once, ExternalSecret resources fail because ESO is not running yet, apps fail because the database is not ready, and the ALB controller does not exist to reconcile Ingress resources. Waves are not optional.

---

## IRSA: How Controllers Get AWS Permissions

Every controller that needs to talk to AWS needs an IAM role. The EBS CSI driver needs to provision volumes, the ALB Controller needs to manage load balancers, External Secrets needs to read from Secrets Manager. Those roles are created by Terraform, not ArgoCD.

The connection is the service account annotation. Terraform creates an IAM role with a trust policy scoped to a specific Kubernetes service account:

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

When the pod starts, the EKS pod identity agent sees the annotation, validates the service account against the OIDC provider, and injects temporary AWS credentials. No static keys, nothing to rotate, no credentials stored anywhere.

Terraform creates the roles. ArgoCD annotates the service accounts. Neither needs to know the details of the other, which is exactly the separation I was after.

---

## Secrets: From AWS to the Pod

The secrets flow follows the same idea. Terraform creates the KMS key and the Secrets Manager entries and never puts credentials directly in Kubernetes.

External Secrets Operator, deployed by ArgoCD, holds an IRSA role that lets it read from Secrets Manager. A `ClusterSecretStore` points ESO at the right AWS region and account. Then `ExternalSecret` resources in each namespace declare which secrets to pull and what to name them as Kubernetes Secrets.

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

Once `terragrunt run --all apply` finishes, here is what has happened without any further manual steps:

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

And just like that, the entire platform assembles itself. One command, walk away, come back to a running cluster.

---

## Further Reading

- [ArgoCD documentation](https://argo-cd.readthedocs.io/)
- [App of Apps pattern](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/)
- [ArgoCD sync waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [IRSA on EKS](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [External Secrets Operator](https://external-secrets.io/)

That's all for now! Thank you for making it to the end.
