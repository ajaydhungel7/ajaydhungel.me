---
title: "System Design 101: The Concepts Behind Every Cloud Architecture"
date: 2026-06-06
draft: true
author: Ajay Dhungel
description: "System design concepts mapped to real AWS services — because understanding the why makes you a better cloud engineer."
tags: ["aws", "devops", "cloud", "system-design"]
tech: ["aws"]
ShowReadingTime: true
ShowToc: true
ShowBreadCrumbs: true
cover:
  image: /imgs/post-007.png
  alt: System Design 101 and Cloud
---

## Introduction

A lot of people learn cloud the way I learned to drive. You figure out which pedal does what, you get comfortable on familiar roads, and it mostly works. Until you hit an unfamiliar intersection and realize you never actually understood traffic flow.

The same thing happens with AWS. You learn to spin up an EC2 instance, deploy a container, configure an S3 bucket. You can get things running. But when someone asks you to design a system that handles a million requests a day without falling over, or explain why the architecture is built the way it is, the gaps start to show.

System design is the traffic flow. Cloud services are just the roads.

This post is about connecting those two things. I am not going to make this abstract. Every concept maps to a real AWS service you can use today.

## Servers: The Starting Point

In system design, a server is just a machine that receives requests and does something with them. It runs your application code, responds to clients, and sits at the center of everything else.

On AWS, that is an EC2 instance. You pick the compute size you need, deploy your application on it, and it starts handling traffic. That is the most direct translation from concept to cloud that exists. One server. One machine. One place where your code lives.

The problem is that one server is a single point of failure. If it goes down, everything goes down. And if traffic spikes, one server can only handle so much before it buckles. This is where the rest of system design comes in.

If you are running containerized workloads, EKS takes this further. Instead of thinking about individual servers, you think about pods, and the cluster manages where they run. The concept is the same, the abstraction is just higher.

## Load Balancing: Spreading the Work

Once you have more than one server, you have a new problem. How does traffic know which server to go to?

That is where a load balancer comes in. Its job is simple: sit in front of your servers, receive incoming requests, and distribute them across your instances so no single one gets overwhelmed. Round-robin, least connections, weighted routing — there are different strategies, but the core idea is the same. The load balancer is the traffic cop.

On AWS, that is the Application Load Balancer. ALB operates at layer 7, which means it understands HTTP. It can route based on paths, headers, and hostnames. You can send requests to `/api` to one target group and `/static` to another. You can run multiple services behind a single ALB and let it figure out where each request belongs.

In EKS, the AWS Load Balancer Controller provisions an ALB automatically when you create an Ingress resource. Your cluster manages the routing rules, and the controller keeps the ALB in sync. You define the intent in Kubernetes, and the infrastructure follows.

## Caching: Stop Repeating Yourself

Here is a question worth sitting with. If a thousand users all request the same data within a minute, how many times should your database actually compute that response?

Once. Maybe not even that, if you cached it from the last time.

Caching is one of the highest-leverage things you can do in system design. You store the result of an expensive operation somewhere fast and cheap, and serve it from there instead of recomputing it every time. The tradeoff is staleness. Cached data is a snapshot. You have to decide how long it can be trusted.

There are two layers where caching matters.

The first is your application layer. This is where ElastiCache comes in. It gives you managed Redis or Memcached sitting between your application and your database. A user logs in, their session goes into Redis. A product page gets requested, the result gets cached with a 60-second TTL. The next 999 requests for that same page never touch the database.

The second is your content layer. Static files, images, scripts, anything that does not change per user, these should be served as close to the user as possible. That is what CloudFront does. It is AWS's content delivery network, a global network of edge locations that cache your content and serve it from wherever the user is geographically closest. A user in Tokyo should not be waiting for a response from a server in Ohio.

Together, ElastiCache and CloudFront handle two very different caching problems. One reduces load on your database. The other reduces latency for your end users.

## Data Storage: Not Everything Belongs in the Same Place

This is one of the concepts I see people get wrong most often. They reach for one storage type for everything, usually a relational database, and then wonder why things get complicated.

Different data has different shapes and different access patterns. That is why there are different storage solutions.

**S3** is for objects. Files, images, backups, logs, static assets, anything you want to store and retrieve by name without a file system. S3 is infinitely scalable, extremely durable, and dirt cheap compared to compute-attached storage. If you are serving assets through CloudFront, your origin is almost always S3. It is also where you want your backups, your logs, and anything that needs to stick around long term.

**EBS** is for your EC2 instances. Think of it as a hard drive that is attached to your server. It lives at the block level, which means your operating system treats it like a disk. Your application files, your database data directory, anything that needs to stay on the instance and survive a reboot, that goes on EBS. The catch is that an EBS volume is attached to one instance at a time. It is not meant to be shared.

**EFS** is for when you need that shared access. It is a managed file system that multiple EC2 instances or containers can mount simultaneously. If you have a batch processing job where multiple workers need to read and write to the same files, or an application that needs a shared filesystem across EKS pods, EFS is what you reach for. In Kubernetes you would use an EFS-backed PersistentVolumeClaim with the ReadWriteMany access mode, something EBS simply cannot do.

Picking the right storage type is not just a performance decision. It is an architecture decision.

## Queues: Decoupling What Should Not Be Coupled

Imagine you have a web application that processes uploaded videos. A user uploads a file, and your server has to transcode it, generate thumbnails, update the database, and send a confirmation email. If you do all of that synchronously, the user waits. If any step fails, the whole thing fails. And if a thousand users upload at the same time, your server is buried.

Queues solve this by decoupling the work from the request. The user uploads the file, your server puts a message on a queue and immediately returns a response. A separate worker process picks up the message and does the heavy lifting asynchronously. The user gets a fast response. The work still gets done. And if the worker crashes halfway through, the message stays on the queue and gets retried.

On AWS, that queue is SQS. Simple Queue Service lets you decouple producers and consumers without managing any infrastructure. You push a message, a consumer polls for it, processes it, and deletes it. You can scale the consumers independently of the producers. You can set visibility timeouts to handle failures gracefully. You can use dead letter queues to catch messages that keep failing so you can investigate later.

This pattern shows up everywhere once you start looking for it. Order processing, notification pipelines, data ingestion, image resizing. Any time you have work that does not need to happen in the same request cycle as the user interaction, a queue is worth considering.

## Putting It Together

Here is a rough picture of what a typical system looks like with all of these pieces in place.

A user makes a request. CloudFront checks if it has the response cached at the edge. If it does, it serves it immediately. If not, the request goes to the ALB. The ALB routes it to one of several EC2 instances, or to an EKS pod if your workloads are containerized. The application checks ElastiCache for the data it needs. If it is there, great. If not, it queries the database, stores the result in ElastiCache, and responds. If the request triggers any background work, a message goes onto an SQS queue and a worker handles it separately. Files and static assets live in S3. Application data that needs to persist lives on EBS. Anything that needs shared access across instances lives on EFS.

None of these are arbitrary choices. Each one exists because of a specific system design need. The CDN exists because latency is a function of distance. The load balancer exists because one server is a single point of failure. The cache exists because database reads are expensive at scale. The queue exists because not all work should block the user.

Understanding the need before the service is what separates someone who can follow a tutorial from someone who can design a system from scratch.

## Closing Thoughts

Cloud providers have done a remarkable job of packaging decades of computer science into managed services. But the concepts underneath have not changed. Caching, load distribution, asynchronous processing, appropriate storage selection, these ideas predate AWS by a long time.

The engineers who get the most out of cloud are not the ones who have memorized the most services. They are the ones who understand what problem each pattern solves, and can recognize when they are looking at one.

That is all for now. Thank you for sticking through to the end, and if any of this sparked a question or a "wait, that is what that is for" moment, I would love to hear it.
