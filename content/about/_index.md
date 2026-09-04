---
draft: false
url: "/about/"
author: Ajay Dhungel
showReadingTime: false
---
{{< resume-preview >}}

---

## Summary
9x AWS Certified Platform & DevOps Engineer and 4-year AWS Community Builder. Maintains SOC 2-compliant EKS and serverless platforms, builds agentic AI systems on Amazon Bedrock, and drives infrastructure automation at scale; presented at AWS Summit Toronto 2025 and 2026.

## Professional Experience

### Freelance Platform & DevOps Engineer
**Upwork** | Remote
*February 2026 - Present*
- Led full EKS engagement for a client — architecture design, technology selection, implementation, and documentation across compute, networking, and storage layers.
- Diagnosed and resolved GitHub Actions pipeline failures across multiple client engagements, covering runner issues, EKS integration, Helm/Kustomize chart deployments, and SNS-Lambda-Slack alerting pipelines.

### DevOps Engineer
**Deskree Technologies Inc.** | Toronto, ON
*March 2025 - February 2026*
- Delivered 99.9% production uptime by leading AWS platform operations across EKS, RDS Aurora, VPC, and ALB.
- Engineered modular Terraform stacks with dev/prod Terraform Cloud workspaces, automating plan/apply workflows, centralizing secrets via AWS Secrets Manager, and bringing all untracked resources under IaC control.
- Built GitHub Actions CI/CD pipelines for containerized Next.js, TypeScript, and Python MCP server services, automating builds, tests, and ECR delivery; bootstrapped EKS clusters with Ansible and deployed ArgoCD via App of Apps for GitOps.
- Reduced monitoring and infrastructure costs by centralizing observability with CloudWatch and Container Insights, developing Python Lambda functions to route alarms to Slack, and rightsizing resources.
- Maintained SOC 2 compliance via Vanta, triaging and remediating flagged controls to ensure continuous audit readiness.

### Cloud Engineer
**Genese Solution** | Kathmandu, Nepal
*March 2022 - December 2023*
- Architected and operated serverless microservice platforms on AWS (Lambda, DynamoDB, API Gateway, CloudFormation), serving as primary AWS engineer across 10+ client accounts.
- Automated infrastructure provisioning and multi-service deployments for Cross River Bank using Terraform, CloudFormation, CodePipeline, and Jenkins, cutting manual release effort.
- Led 45+ AWS Well-Architected Framework Reviews, producing architecture diagrams in Lucidchart and Draw.io to surface risks and align clients with AWS best practices.
- Hardened security across multiple client AWS environments by executing IAM audits and vulnerability assessments, implementing data protection controls in regulated cloud environments.

## Projects

**openclaw-lightsail-setup** | AWS Summit Toronto 2026 | Terraform, Ansible, Amazon Bedrock, AWS Lightsail
- Automated full deployment of the OpenClaw personal AI assistant on AWS Lightsail — Terraform provisions the instance, static IP, firewall, and Bedrock IAM role; Ansible configures agents, MCP skills, and Telegram in a single terraform apply.
- Integrated Claude Sonnet via Amazon Bedrock with Telegram, Google Workspace (Gmail, Calendar), and Notion MCP for a multi-agent personal assistant; demo presented at AWS Summit Toronto 2026.

**bedrock-agents-collab** | AWS Summit Toronto 2025 | Terraform, Amazon Bedrock, Python
- Built Terraform infrastructure for a multi-agent collaboration system on Amazon Bedrock; demo presented at AWS Summit Toronto 2025.
- Provisioned Bedrock agents, orchestration layer, and supporting AWS infrastructure fully as code.

**k8s-gitops** | Terraform, Terragrunt, ArgoCD, Jenkins, EKS
- Implemented a full GitOps lifecycle on AWS EKS, deploying FastAPI, Nginx, MongoDB, and Redis via ArgoCD App of Apps.
- Provisioned and managed cluster infrastructure with Terraform and Terragrunt; automated deployments through Jenkins pipelines.

**railsflow-ci** | GitHub Actions, EKS, Helm, Terragrunt, Ruby
- Built a production-grade CI/CD pipeline for Ruby on Rails targeting EKS with Helm chart deployments.
- Automated test, build, and deploy stages via GitHub Actions with Terragrunt-managed infrastructure.

**ai-cv-tailor** | Claude Code, Claude API, LaTeX, XeLaTeX | Active
- Built an AI-native CV tailoring pipeline — drop in a job description and Claude reads the JD, makes tailoring decisions, and compiles a submission-ready PDF.
- Master resume lives in a single LaTeX source; Claude adjusts the title, summary, and bullets per role using a variant library, keeping the master untouched.

## Education

**Lambton College** | Post-Graduate Certificate in DevOps For Cloud Computing | 2025
Dean's List

**Tribhuvan University** | Bachelor of Information Management | 2022

## Technical Skills

**IaC**: Terraform, Terragrunt, Ansible, CloudFormation

**Containers**: Kubernetes (EKS), Docker, Helm, ArgoCD

**CI/CD**: GitHub Actions, Jenkins, CodePipeline, GitOps

**Scripting**: Python, Bash, Linux

**Cloud**: AWS (EKS, ECS, RDS Aurora, Lambda, VPC, ALB, ECR, Secrets Manager, IAM, SES, Bedrock)

**Observability**: CloudWatch, Container Insights, Prometheus, Grafana, Datadog, alerting

**Security**: DevSecOps, SOC 2, Vanta, shift-left practices

## Certifications

- **AWS Certified DevOps Engineer – Professional** | Sep 2024
- **AWS Certified Solutions Architect – Professional** | Jan 2026
- **AWS Certified Generative AI Developer – Professional** | Jan 2026
- **AWS Certified CloudOps Engineer – Associate** | Oct 2025
- **AWS Certified Developer – Associate** | Sep 2025
- **AWS Certified Machine Learning Engineer – Associate** | Feb 2025
- **AWS Certified Solutions Architect – Associate** | Jun 2023
- **HashiCorp Certified: Terraform Associate (003)** | Dec 2023

## Community & Accomplishments

- AWS Community Builder (2023–2026) | [Community Builders Profile](https://builder.aws.com/community/@ajaya)
- All Builders Welcome Grant | Amazon Web Services, 2025; attended re:Invent 2025 in Las Vegas
- Speaker: AWS Summit Toronto 2025 — Multi-Agent Collaboration on Amazon Bedrock
- Speaker: AWS Summit Toronto 2026, AWS Community Lounge — Building a Personal AI Assistant with OpenClaw on AWS; ~200 attendees; Community Lounge sessions ranked highest CSAT at Summit
- FIFA World Cup 2026 Volunteer | Pre-Match Ceremonies, Toronto Stadium (Jan 2026 – Jul 2026)
