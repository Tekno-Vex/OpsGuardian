# OpsGuardian
### Autonomous Cloud SRE Multi-Agent System

> *Detects, diagnoses, and remediates EC2 infrastructure failures without human intervention — reducing MTTR from 15 minutes to under 90 seconds.*

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Multi--Service-FF9900?style=flat&logo=amazonaws&logoColor=white)
![React](https://img.shields.io/badge/React-Dashboard-61DAFB?style=flat&logo=react&logoColor=black)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-Nova_Micro-FF9900?style=flat&logo=amazonaws&logoColor=white)
![Cost](https://img.shields.io/badge/Infrastructure_Cost-%240.00%2Fmonth-2ECC71?style=flat)

---

## The Problem

Cloud infrastructure fails at **machine speed**. Human debugging happens at **human speed**.

Traditional SRE tooling relies on hardcoded automation scripts — when an unknown failure mode occurs, those scripts fail silently. OpsGuardian replaces deterministic scripts with **dynamic LLM-driven reasoning**: the system reads, understands, and responds to failures it has never explicitly seen before, using semantic similarity search to match novel alarms to known remediation patterns.

---

## Key Metrics

| Metric | Value |
|---|---|
| MTTR Reduction | 15 min → **<90 seconds** |
| Infrastructure Cost | **$0.00/month** (100% AWS Free Tier) |
| Alarm Types Monitored | CPU, Memory, Disk (extensible to any CloudWatch metric) |
| Specialized AI Agents | **6** (Watcher, Investigator, Architect, Critic, Executor, Logger) |
| AWS Services Integrated | **10** (Lambda, Step Functions, Bedrock, DynamoDB, S3, CloudWatch, SNS, SSM, API Gateway, EC2) |
| RAG Embedding Dimensions | **1,024** (Amazon Titan Embeddings V2) |
| Safety Blocklist Rules | **10 patterns** (blocks all destructive command patterns) |
| Semantic Search Threshold | **0.25 cosine similarity** (tuned empirically across all alarm types) |

---

## Architecture

OpsGuardian is a **true Multi-Agent System (MAS)** — six specialized AI agents, each a separate AWS Lambda function, orchestrated by AWS Step Functions into a distributed pipeline with fault tolerance, semantic reasoning, safety gates, and human oversight.

```
CloudWatch Alarm
      │
      ▼
  SNS Topic
      │
      ▼
┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│   Watcher   │────▶│ Investigator  │────▶│  Architect  │
│ (Entry Point│     │ (RAG Search)  │     │ (LLM Reason)│
└─────────────┘     └───────────────┘     └─────────────┘
                                                 │
                          ┌──────────────────────┘
                          ▼
                    ┌───────────┐
                    │  Critic   │  ◀── 10-pattern safety blocklist
                    └───────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       Low/Medium Severity      High/Critical Severity
              │                       │
              ▼                       ▼
        ┌──────────┐         ┌─────────────────┐
        │ Executor │         │ WaitForApproval │  ◀── Human-in-the-Loop
        │  (SSM)   │         │  (Email Gate)   │
        └──────────┘         └─────────────────┘
              │
              ▼
        ┌──────────┐
        │  Logger  │  ──▶  DynamoDB audit trail
        └──────────┘
```

---

## The Six-Agent Pipeline

| Agent | Type | AWS Service | Responsibility |
|---|---|---|---|
| **Watcher** | Simple Reflex | CloudWatch + SNS | Monitors metrics, triggers pipeline on threshold breach |
| **Investigator** | Model-Based Reflex | Lambda + S3 + Bedrock Titan | Semantic RAG search across vector knowledge base |
| **Architect** | Goal-Based | Lambda + Bedrock Nova Micro | LLM reasoning to determine exact remediation command |
| **Critic** | Safety Agent | Lambda | Blocklist validation, prevents destructive command execution |
| **Executor** | Action Agent | Lambda + SSM | Executes approved commands on EC2 via Systems Manager |
| **Logger** | Learning Agent | Lambda + DynamoDB | Persists full incident audit trail for pattern analysis |

---

## Intelligence Layer: Semantic RAG

OpsGuardian doesn't just pattern-match, it **understands** alarm descriptions.

The Investigator agent uses **Amazon Titan Embeddings V2** to generate 1,024-dimensional vectors for each runbook entry offline. At runtime, the incoming alarm description is embedded and compared via **cosine similarity** against the knowledge base — no exact keyword match required.

```
Query: "server is overloaded and unresponsive"
         │
         ▼
  Titan Embeddings V2
  (1024-dim vector)
         │
         ▼
  Cosine Similarity Search
  against S3 knowledge base
         │
         ▼
  HighCPU runbook entry — similarity: 0.52 ✅
```

This enables the agent to correctly handle failure descriptions it has never seen before — the core requirement for production-grade autonomous remediation.

---

## Safety Architecture

OpsGuardian implements **three independent safety layers**:

**Layer 1 — Critic Agent Blocklist**
Every proposed command is validated against 10 destructive patterns before execution:
- `rm -rf /` and variants
- `dd if=/dev/zero` (disk wipe)
- Fork bombs
- Full partition overwrites

**Layer 2 — Human-in-the-Loop Approval Gate**
High and critical severity incidents pause the pipeline entirely using AWS Step Functions callback tokens. An approval email is sent to the on-call engineer with full incident context. The pipeline resumes only on explicit Approve click — or expires after 15 minutes.

**Layer 3 — Principle of Least Privilege IAM**
Every Lambda function has a scoped inline IAM policy. No function has permissions beyond what its specific role requires.

---

## AWS Services Architecture

| Service | Role | Free Tier Monthly Usage |
|---|---|---|
| AWS Lambda | 6 agent functions + 2 API functions | ~200 invocations |
| AWS Step Functions | Pipeline orchestration state machine | ~500 transitions |
| Amazon DynamoDB | Incident state + pending approvals | <5MB |
| Amazon S3 | Vector knowledge base + React dashboard | <10MB |
| Amazon CloudWatch | Metric alarms + agent logging | 3 alarms |
| Amazon Bedrock Nova Micro | LLM reasoning (Architect agent) | ~50 calls/month |
| Amazon Titan Embeddings V2 | Vector generation (Investigator agent) | ~10 calls/month |
| AWS SSM | Remote command execution on EC2 | Per incident |
| Amazon SNS | Alarm notifications + approval emails | <50/month |
| API Gateway REST | Frontend data endpoint + approval handler | <1,000/month |

**Total infrastructure cost: $0.00/month**

---

## Chaos Engineering

All three failure modes are validated end-to-end with purpose-built fault injection scripts:

| Chaos Script | Method | Threshold | Verified |
|---|---|---|---|
| `chaos_cpu.py` | Multiprocessing burns all cores simultaneously (bypasses Python GIL) | CPU ≥ 80% | ✅ |
| `chaos_memory.py` | Allocates 1MB chunks reading `/proc/meminfo` until 90% RAM used | Memory ≥ 70% | ✅ |
| `chaos_disk.sh` | Writes 1GB files to root partition until 75% disk usage | Disk ≥ 80% | ✅ |

Each test triggers the full 6-agent pipeline and verifies automatic remediation without human intervention.

---

## Mission Control Dashboard

A real-time React dashboard deployed on S3 polls the REST API every 3 seconds, displaying:

- Live pipeline status (green/red health badge)
- Incident cards with alarm type, proposed command, and similarity score
- Total incidents / resolved / failed counters
- Full audit trail with DynamoDB-backed persistence

---

## Repository Structure

```
opsguardian/
├── backend-agent/              # All Lambda function code (Python 3.12)
│   ├── watcher.py              # Entry point, starts Step Functions
│   ├── investigator.py         # RAG vector search agent
│   ├── architect.py            # Bedrock LLM reasoning agent
│   ├── critic.py               # Safety validation agent
│   ├── executor.py             # SSM command execution agent
│   ├── logger.py               # DynamoDB audit trail agent
│   ├── api_handler.py          # REST API Lambda (GET /status)
│   ├── approval_gate.py        # Human-in-Loop gate
│   └── approval_handler.py     # Approve/deny click handler
├── chaos-engineering/          # Fault injection test scripts
│   ├── chaos_cpu.py            # Multi-core CPU stress test
│   ├── chaos_memory.py         # RAM allocation stress test
│   └── chaos_disk.sh           # Root partition fill test
├── frontend-dashboard/         # React Mission Control UI
│   └── src/App.js              # Main component, live polling
├── infrastructure/             # IAM policies as code
│   ├── lambda-role-policy.json
│   └── ec2-role-policy.json
└── knowledge-base/             # RAG data and embedding tools
    ├── runbook_rich.json        # Runbook with descriptions + severity
    └── build_embeddings.py     # Titan Embeddings vector builder
```

---

## Key Engineering Decisions

| Decision | Choice | Why | Alternative Considered |
|---|---|---|---|
| Agent Framework | Native boto3 SDK | Zero latency, no persistent servers, free tier compatible | LangChain, AutoGen |
| LLM | Nova Micro + Titan Embeddings V2 | Fractions of a cent per call, sufficient reasoning capability | Claude/GPT-4 (10-100x more expensive) |
| Orchestration | AWS Step Functions Standard | Visual workflow, audit history, callback tokens for Human-in-the-Loop | EventBridge pipes, SQS queues |
| Vector Store | S3 JSON file | Free, sufficient for <100 runbook entries, no additional service | OpenSearch, Pinecone (cost money) |
| Compute | Lambda (serverless) | No idle cost, auto-scales, event-driven naturally | EC2 always-on agent |
| Embeddings | Titan Embeddings V2 (1024-dim) | Native to AWS, no cross-cloud API calls | OpenAI text-embedding-3-small |

---

## Tech Stack

**Cloud:** AWS Lambda · Step Functions · Bedrock · DynamoDB · S3 · CloudWatch · SNS · SSM · API Gateway · EC2

**AI/ML:** Amazon Bedrock Nova Micro · Titan Embeddings V2 · RAG · Cosine Similarity · Semantic Search

**Backend:** Python 3.12 · boto3 · REST API

**Frontend:** React · S3 Static Hosting · API Gateway

**Infrastructure:** IAM · Principle of Least Privilege · Chaos Engineering

---

*Built by [Vivekanandhan Kathirvel](https://www.linkedin.com/in/vivekanandhan-kathirvel-828b20253/) — USF M.S. Computer Science*
