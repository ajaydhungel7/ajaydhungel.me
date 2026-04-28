---
title: "Kubernetes Gateway API: The End of Ingress Annotation Hell"
date: 2026-04-28
draft: false
author: Ajay Dhungel
description: "A deep dive into the Kubernetes Gateway API, what problems it solves over Ingress, and real YAML examples using Nginx, AWS ALB, and the AWS Gateway API controller."
tags: ["kubernetes", "networking", "gateway-api", "aws", "devops"]
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
---

## Introduction

If you have spent any meaningful time running workloads on Kubernetes, you have probably dealt with Ingress resources. They work. They get traffic into your cluster. But the moment you need something beyond basic host and path routing, you end up buried in controller-specific annotations that nobody else understands, that break the moment you switch controllers, and that give your application teams zero autonomy.

The Kubernetes Gateway API is the project's answer to that problem. It is not just a newer version of Ingress. It is a fundamentally different way of thinking about traffic routing in a cluster, one that actually maps to how teams are structured and how infrastructure responsibility is divided.

This post walks through what Ingress could and could not do, why the Gateway API exists, and what it looks like in practice with Nginx, AWS ALB, and the AWS Gateway API controller.

---

## The Ingress Problem

The Ingress spec itself is minimal by design. Out of the box, it gives you:

- Host-based routing
- Path-based routing
- TLS termination via a Kubernetes secret

That covers the basics, but anything beyond that required annotations. And annotations were where things got messy.

### What annotations unlocked

Here is what you could do with the Nginx ingress controller using annotations:

**Canary deployments:**
```yaml
nginx.ingress.kubernetes.io/canary: "true"
nginx.ingress.kubernetes.io/canary-weight: "20"
```

**Redirects:**
```yaml
nginx.ingress.kubernetes.io/permanent-redirect: "https://new.example.com"
```

**Path rewrites:**
```yaml
nginx.ingress.kubernetes.io/rewrite-target: /$2
```

**Rate limiting:**
```yaml
nginx.ingress.kubernetes.io/limit-rps: "10"
```

**Timeouts:**
```yaml
nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
nginx.ingress.kubernetes.io/proxy-connect-timeout: "10"
```

And with the AWS ALB controller, the equivalent for weighted routing looked completely different:

```yaml
alb.ingress.kubernetes.io/actions.forward-config: |
  {
    "targetGroups": [
      {"serviceName": "app-stable", "servicePort": 80, "weight": 80},
      {"serviceName": "app-canary", "servicePort": 80, "weight": 20}
    ]
  }
```

Same concept, completely different syntax, zero portability. If you switched controllers, you rewrote everything.

### What was not possible at all

Some things were simply off the table regardless of which controller you used or how many annotations you stacked:

**Cross-namespace routing.** An Ingress resource can only route traffic to services in its own namespace. Full stop. If your gateway lived in `infra` and your app lived in `payments`, there was no clean way to connect them.

**Meaningful multi-tenancy.** There was no concept of "this team can manage routes for their hostname but cannot touch anyone else's." If an application team needed to add or change a route, they needed write access to the Ingress resource itself. That meant one team could accidentally overwrite another team's routing rules.

**Portable advanced routing.** Header-based routing, traffic splitting, request mirroring, URL rewrites -- all of these depended on annotations that were specific to the controller you happened to be running. Your YAML was tied to your infrastructure choice in a way that made migrations painful.

**TCP and UDP routing.** Ingress is an HTTP-only API. Routing raw TCP or UDP traffic required separate ConfigMap hacks that felt bolted on because they were.

---

## What the Gateway API Changes

The Gateway API, now part of the official Kubernetes SIG Network project, was built around four principles: role-oriented, portable, expressive, and extensible.

The portable and expressive parts are straightforward. The interesting one is role-oriented.

### A proper separation of responsibility

The Gateway API splits traffic routing across three resource types, each owned by a different persona in your organization.

![Gateway API Role Model](/imgs/gateway-api-roles.png)

**Infrastructure providers** (think AWS, GCP, your platform team) manage `GatewayClass`. This is a cluster-scoped resource that defines which controller handles traffic, similar to `StorageClass` for persistent volumes.

**Cluster operators** manage `Gateway`. This is the actual load balancer or listener configuration. They decide which ports are open, which protocols are accepted, and which namespaces are allowed to attach routes.

**Application developers** manage `HTTPRoute` (or `GRPCRoute`, etc.). They define the routing rules for their specific application without ever touching the gateway itself.

This means an application team can deploy a new service and add a route to expose it without filing a ticket to the platform team. And the platform team can enforce policies at the Gateway level without blocking developers.

### The standard API resources (v1.2)

Before jumping into examples, here is what is stable and production-ready today in the standard channel:

| Resource | API Version |
|---|---|
| GatewayClass | v1 |
| Gateway | v1 |
| HTTPRoute | v1 |
| GRPCRoute | v1 |
| ReferenceGrant | v1beta1 |

TCP, TLS, and UDP routes are still in the experimental channel. For most web workloads, the standard channel is all you need.

---

## Before and After: Real YAML Examples

### The Ingress way with Nginx

This is what a typical Nginx Ingress setup looks like. Basic routing works fine, but notice how the canary deployment requires a second Ingress object and controller-specific annotations:

```yaml
# Main ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  namespace: production
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
spec:
  tls:
    - hosts:
        - app.example.com
      secretName: app-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-stable
                port:
                  number: 80
---
# Canary ingress -- separate object, same host
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-canary
  namespace: production
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "20"
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-canary
                port:
                  number: 80
```

It works, but splitting one logical routing concern across two resources with annotations controlling the relationship is not great. And this only works with Nginx. Switch to ALB and you start over.

### The Ingress way with AWS ALB controller

The ALB controller uses a completely different annotation vocabulary:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  namespace: production
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789:certificate/abc123
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/actions.weighted-routing: |
      {
        "type": "forward",
        "forwardConfig": {
          "targetGroups": [
            {"serviceName": "app-stable", "servicePort": 80, "weight": 80},
            {"serviceName": "app-canary", "servicePort": 80, "weight": 20}
          ]
        }
      }
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: weighted-routing  # references the annotation action
                port:
                  name: use-annotation
```

The annotation-as-action pattern is particularly awkward here. The backend service name is literally `weighted-routing`, referencing an annotation key. This is not standard Kubernetes, and anyone reading this for the first time has no idea what is happening.

---

### The Gateway API way with Nginx Gateway Fabric

Now here is the same setup using the Gateway API with the Nginx Gateway Fabric controller. The platform team manages the `GatewayClass` and `Gateway`. The application team only touches `HTTPRoute`.

```yaml
# Platform team owns this
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: nginx
spec:
  controllerName: gateway.nginx.org/nginx-gateway-controller
---
# Platform team owns this too
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: infra
spec:
  gatewayClassName: nginx
  listeners:
    - name: https
      port: 443
      protocol: HTTPS
      tls:
        mode: Terminate
        certificateRefs:
          - name: app-tls
            namespace: infra
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              gateway-access: "true"
---
# Application team owns this -- different namespace
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-app
  namespace: production
spec:
  parentRefs:
    - name: main-gateway
      namespace: infra
  hostnames:
    - app.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: app-stable
          port: 80
          weight: 80
        - name: app-canary
          port: 80
          weight: 20
```

Traffic weighting is a first-class field, not an annotation. The application team writes a clean HTTPRoute in their own namespace. The platform team controls what namespaces can attach via the `allowedRoutes` selector. Nobody needs to coordinate on every change.

To allow the cross-namespace reference from `production` to `infra`, you add a `ReferenceGrant`:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-production-routes
  namespace: infra
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: production
  to:
    - group: ""
      kind: Secret
      name: app-tls
```

---

### The Gateway API way with AWS (Gateway API controller for AWS)

AWS has a Gateway API controller that uses an Application Load Balancer as the underlying implementation. The setup follows the same pattern -- the only thing that changes is the `GatewayClass` and some AWS-specific fields.

```yaml
# Installed by AWS when you set up the controller
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: aws-alb
spec:
  controllerName: gateway.k8s.aws/alb
---
# Platform team configures the ALB
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: alb-gateway
  namespace: infra
  annotations:
    gateway.alb.k8s.aws/scheme: internet-facing
    gateway.alb.k8s.aws/target-type: ip
    gateway.alb.k8s.aws/certificate-arn: arn:aws:acm:us-east-1:123456789:certificate/abc123
spec:
  gatewayClassName: aws-alb
  listeners:
    - name: https
      port: 443
      protocol: HTTPS
      tls:
        mode: Terminate
        certificateRefs:
          - name: app-tls
            namespace: infra
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              gateway-access: "true"
---
# Application team deploys this -- identical structure to the Nginx example
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-app
  namespace: production
spec:
  parentRefs:
    - name: alb-gateway
      namespace: infra
  hostnames:
    - app.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
          headers:
            - name: X-Version
              value: v2
      backendRefs:
        - name: app-v2
          port: 8080
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: app-stable
          port: 80
          weight: 80
        - name: app-canary
          port: 80
          weight: 20
```

Notice that the `HTTPRoute` is identical to the Nginx example. The application team does not know or care whether the underlying load balancer is Nginx or an AWS ALB. That is the portability the Gateway API was designed to deliver.

---

## Installing the Gateway API CRDs

The Gateway API is not bundled with Kubernetes itself. You install it separately as CRDs:

```bash
# Standard channel (recommended for production)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# Experimental channel (adds TCPRoute, TLSRoute, UDPRoute, and more)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/experimental-install.yaml
```

After that, you install your specific controller (Nginx Gateway Fabric, AWS Gateway API controller, Cilium, Envoy Gateway, etc.) which registers itself as a `GatewayClass`.

---

## What This Means Practically

If you are running a small single-team cluster, the difference between Ingress and Gateway API is mostly syntax. Both get the job done.

The real value shows up at scale. When you have multiple teams sharing a cluster, when you need to enforce that the platform team controls the load balancer config but app teams control their own routes, when you want to do a canary rollout without touching the gateway configuration, when you need to move between cloud providers or controllers without rewriting all your routing config -- that is where the Gateway API's design actually pays off.

The official spec describes it as balancing "distributed flexibility and centralized control." That is a reasonable summary. Application developers get the autonomy to manage their own routes. Platform teams keep control of the infrastructure. And the routing configuration itself is portable across any compliant implementation.

Ingress got Kubernetes networking to where it needed to be in the early years. Gateway API is where it needs to go next.

---

## Further Reading

- [Kubernetes Gateway API official docs](https://gateway-api.sigs.k8s.io/)
- [API Overview and concepts](https://gateway-api.sigs.k8s.io/concepts/api-overview/)
- [Implementations list](https://gateway-api.sigs.k8s.io/implementations/)
- [AWS Gateway API Controller](https://www.gateway-api-controller.eks.aws.dev/)
