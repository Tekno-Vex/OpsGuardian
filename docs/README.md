# OpsGuardian
### Autonomous Cloud Site Reliability Engineering Agent

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Free%20Tier-FF9900?style=flat&logo=amazonaws&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-Nova_Micro-7B2FBE?style=flat&logo=amazonaws&logoColor=white)
[![OpsGuardian CI/CD Pipeline](https://github.com/Tekno-Vex/OpsGuardian/actions/workflows/deploy.yml/badge.svg)](https://github.com/Tekno-Vex/OpsGuardian/actions/workflows/deploy.yml)
![Cost](https://img.shields.io/badge/Infrastructure_Cost-%240.00%2Fmonth-00C853?style=flat)

> **OpsGuardian solves the Asymmetric Failure Problem** — cloud systems fail at machine speed, but manual debugging happens at human speed. OpsGuardian closes that gap with a 6-agent autonomous pipeline that detects, diagnoses, and remediates infrastructure failures in under **90 seconds** — without human intervention.

---

## Live Demo

### System starts healthy — no incidents recorded
![OpsGuardian Empty State](OpsGuardian1.gif)

### Chaos script triggers — OpsGuardian detects, diagnoses, and auto-remediates
![OpsGuardian Resolving Incident](OpsGuardian2.gif)

**[View Live Mission Control Dashboard](http://opsguardian-dashboard.s3-website.us-east-2.amazonaws.com/)**

---

## Architecture

![OpsGuardian Architecture](architecture.png)

OpsGuardian is a **Multi-Agent System (MAS)** — six specialized AI agents, each an independent AWS Lambda microservice, orchestrated by AWS Step Functions into a fault-tolerant distributed pipeline.

---

## Key Metrics

| Metric | Value |
|---|---|
| MTTR Reduction | 15 min → **<90 seconds** |
| Infrastructure Cost | **$0.00/month** (100% AWS Free Tier) |
| Alarm Types Monitored | CPU, Memory, Disk |
| Specialized AI Agents | **6** independent Lambda microservices |
| AWS Services Integrated | **13** |
| RAG Embedding Dimensions | **1,024** (Amazon Titan Embeddings V2) |
| Safety Blocklist Patterns | **10** |

---

## How To Run OpsGuardian

### Prerequisites
- AWS Account (Free Tier sufficient)
- AWS CLI installed and configured (`aws configure`)
- Python 3.12
- Node.js 18+
- Git

### Step 1 — Clone the Repository
git clone https://github.com/Tekno-Vex/OpsGuardian.git
cd OpsGuardian

### Step 2 — Deploy AWS Infrastructure
aws cloudformation deploy 
--template-file infrastructure/template.yaml 
--stack-name OpsGuardian 
--parameter-overrides AlertEmail=your@email.com 
--capabilities CAPABILITY_NAMED_IAM 
--region us-east-2
This creates all DynamoDB tables, S3 buckets, SNS topics, and IAM roles automatically.

### Step 3 — Build and Upload Vector Knowledge Base
cd knowledge-base
pip install boto3
python build_embeddings.py
This generates 1,024-dimension vectors for each runbook entry and uploads to S3.

### Step 4 — Deploy Lambda Functions
Push any change to main branch — GitHub Actions automatically deploys all 11 Lambda functions.

Or deploy manually:
zip -j watcher.zip backend-agent/watcher.py
aws lambda update-function-code 
--function-name OpsGuardian-Watcher 
--zip-file fileb://watcher.zip
Repeat for each Lambda function in backend-agent/.

### Step 5 — Deploy the React Dashboard
cd opsguardian-ui
npm install
npm run build
aws s3 sync build/ s3://opsguardian-dashboard-YOUR-ACCOUNT-ID --delete

### Step 6 — Run a Chaos Test
Connect to the EC2 Victim-Server via AWS Systems Manager Session Manager (no SSH required):
python3 chaos_cpu.py    # CPU spike test
python3 chaos_memory.py # Memory exhaustion test
bash chaos_disk.sh      # Disk fill test

### Step 7 — Working condition
- Open the S3 dashboard URL in your browser
- Go to AWS Step Functions → OpsGuardian-Pipeline → Executions
- Watch each agent execute in real time
- Check DynamoDB → OpsGuardian_State for the incident record

### Environment Variables Required (set in Lambda Console)
| Lambda | Variable | Value |
|---|---|---|
| OpsGuardian-Watcher | STATE_MACHINE_ARN | Your Step Functions ARN |
| OpsGuardian-Investigator | S3_BUCKET | Your knowledge base bucket name |
| OpsGuardian-ApprovalGate | SNS_TOPIC_ARN | OpsGuardian-Email-Alerts ARN |
| OpsGuardian-ApprovalGate | API_BASE_URL | Your API Gateway URL |
| OpsGuardian-LearningElement | S3_BUCKET | Your knowledge base bucket name |
| OpsGuardian-LearningElement | SNS_TOPIC_ARN | OpsGuardian-Email-Alerts ARN |

## The Six-Agent Pipeline

| Agent | Type | Responsibility |
|---|---|---|
| **Watcher** | Simple Reflex | Monitors CPU/Memory/Disk via CloudWatch, triggers pipeline on breach |
| **Investigator** | Model-Based Reflex | Semantic RAG search across 1,024-dimension vector knowledge base |
| **Architect** | Goal-Based | Bedrock Nova Micro LLM reasoning to determine exact remediation command |
| **Critic** | Safety Agent | 10-pattern blocklist validation before any execution |
| **Executor** | Action Agent | Remote command execution on EC2 via AWS SSM |
| **Logger** | Learning Agent | Full incident audit trail + command outcome tracking in DynamoDB |

```
CloudWatch Alarm → SNS → Watcher → Investigator → Architect → Critic
                                                                  │
                                                     ┌────────────┴────────────┐
                                                 Medium/Low              High/Critical
                                                     │                        │
                                                  Executor          WaitForApproval
                                                     │               (Email Gate)
                                                     └──────┬─────────────────┘
                                                            │
                                                         Logger → DynamoDB
```

---

## Intelligence Layer: Semantic RAG

The Investigator uses **Amazon Titan Embeddings V2** to generate 1,024-dimensional vectors for each runbook entry. At runtime, alarm descriptions are embedded and matched via **cosine similarity** — correctly identifying the right remediation even for failure descriptions the system has never seen before.

```
Query: "server is overloaded and unresponsive"
    → Titan Embeddings V2 (1,024-dim vector)
    → Cosine similarity search across S3 knowledge base
    → HighCPU entry matched at 52% confidence ✅
    → Fix passed to Architect for LLM reasoning
```

---

## Safety Architecture

**Critic Agent** — Every Bedrock-proposed command is validated against a 10-pattern destructive command blocklist (`rm -rf /`, `mkfs`, fork bombs, disk wipes) before any execution.

**Human-in-the-Loop** — High/critical severity incidents pause the Step Functions pipeline using callback tokens. The on-call engineer receives a full-context email with one-click Approve/Deny links. Auto-expires after 15 minutes.

**Principle of Least Privilege** — Separate IAM roles for EC2 and Lambda with scoped inline policies.

---

## Self-Healing Runbook

A weekly **EventBridge-scheduled Lambda** scans DynamoDB incident history, identifies commands below 50% success rate, asks Bedrock to suggest better alternatives, and writes improvement suggestions to S3 for human review before going live.

---

## Key Engineering Decisions

| Decision | Choice | Why |
|---|---|---|
| Agent framework | Native `boto3` SDK | Zero latency, no persistent servers, free tier compatible |
| LLM | Nova Micro + Titan Embeddings V2 | Fractions of a cent per call, native AWS integration |
| Orchestration | AWS Step Functions Standard | Visual workflow, callback tokens for Human-in-the-Loop |
| Vector store | S3 JSON | Free, zero ops overhead for <100 runbook entries |
| SNS topology | Two separate topics | Prevents infinite loop between agent triggers and human notifications |

---

## Lessons Learned

**SNS infinite loop** — Routing approval emails through the same SNS topic that triggers agents caused recursive Lambda invocations generating 1,000+ emails. Fixed with separate `OpsGuardian-Alerts` (agent triggers) and `OpsGuardian-Email-Alerts` (human notifications) topics.

**Python GIL limitation** — Single-threaded chaos script plateaued at 50% CPU. Fixed with `multiprocessing.Process` spawning one process per core for true multi-core saturation.

**Titan embedding calibration** — Titan V2 produces conservative scores (0.25–0.52). Threshold tuned empirically rather than assuming standard 0.7+ cutoffs.

---

## Tech Stack

**Cloud:** `Lambda` `Step Functions` `DynamoDB` `S3` `CloudWatch` `SNS` `SSM` `API Gateway` `EC2` `EventBridge` `IAM` `CloudWatch Agent` `Amazon Bedrock`

**AI/ML:** `Nova Micro` `Titan Embeddings V2` `RAG` `Cosine Similarity` `Prompt Engineering`

**Application:** `Python 3.12` `boto3` `React 18` `Recharts` `Axios`

---

## Code Attribution

This project was independently designed and implemented by
Vivekanandhan Kathirvel for the Intro to Agentic AI course at USF.

### AI Assistance
Claude was used throughout this project as a top-down
learning tool. I used Claude to understand concepts, learn services, and guide implementation. All code was reviewed, tested, debugged, and validated by me personally throughhands-on implementation in AWS.

### What I Implemented Myself
The core agent logic was written and iterated with help of claude as follows:
- All 11 Lambda functions (boto3 SDK calls, agent logic, error handling)
- AWS Step Functions state machine definition (JSON workflow)
- RAG pipeline (cosine similarity math, embedding integration)
- Critic safety blocklist and pre-flight verification logic
- CloudWatch alarm configuration and SNS topic architecture
- DynamoDB schema design and query logic
- CloudFormation infrastructure template
- GitHub Actions CI/CD workflow

Utilized my AWS Cloud Practitioner and AI practitioner knowledge to do so

### Where I Used Heavy Guidance and Top-Down Learning
- React dashboard (App.js), learned React patterns with Claude's help
  as I had little React experience
- Recharts integration for the analytics tab
- CSS styling and dashboard layout
- Setup the API Gateway, as is not the main focus of this project

### Open Source Libraries Used
- boto3 (Apache 2.0): https://github.com/boto/boto3
- React (MIT): https://github.com/facebook/react
- Recharts (MIT): https://github.com/recharts/recharts
- Axios (MIT): https://github.com/axios/axios

*Built by [Vivekanandhan Kathirvel](https://www.linkedin.com/in/vivekanandhan-kathirvel-828b20253/) — USF M.S. Computer Science*
