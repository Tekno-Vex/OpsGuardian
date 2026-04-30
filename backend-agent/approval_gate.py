"""OpsGuardian — Approval Gate
=============================
Human-in-the-Loop safety gate for high-severity incidents.
Receives the Step Functions task token, saves the pending
approval to DynamoDB with a 15-minute TTL, and sends the
on-call engineer a full-context approval email via SNS with
one-click Approve and Deny links.
"""

import boto3
import json
import os
from datetime import datetime, timedelta

REGION       = 'us-east-2'
DYNAMO_TABLE = 'OpsGuardian_PendingApprovals'
SNS_TOPIC    = os.environ.get('SNS_TOPIC_ARN', '')
API_BASE_URL = os.environ.get('API_BASE_URL', '')

dynamo = boto3.resource('dynamodb', region_name=REGION)
sns    = boto3.client('sns',        region_name=REGION)

def lambda_handler(event, context):
    print(f"ApprovalGate activated. Incident: {event.get('incident_id')}")
    task_token  = event.get('taskToken')
    incident_id = event.get('incident_id')
    instance_id = event.get('instance_id')
    alarm_type  = event.get('alarm_type')
    command     = event.get('proposed_command')
    reasoning   = event.get('reasoning', '')
    severity    = event.get('rag_severity', 'high')
    sim_score   = event.get('similarity_score', 0)
    approval_id = incident_id

    expires_at = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())
    table = dynamo.Table(DYNAMO_TABLE)
    table.put_item(Item={
        'approval_id':  approval_id,
        'incident_id':  incident_id,
        'task_token':   task_token,
        'instance_id':  instance_id,
        'alarm_type':   alarm_type,
        'command':      command,
        'reasoning':    reasoning,
        'severity':     severity,
        'status':       'Pending',
        'created_at':   datetime.utcnow().isoformat(),
        'expires_at':   expires_at
    })
    print(f"Saved approval request to DynamoDB: {approval_id}")

    approve_url = f"{API_BASE_URL}/approve/{approval_id}/approve"
    deny_url    = f"{API_BASE_URL}/approve/{approval_id}/deny"

    confidence = f"{float(sim_score)*100:.1f}%" if sim_score != 'N/A' else 'N/A'
    message = f"""
🚨 OpsGuardian Approval Required

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCIDENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instance:   {instance_id}
Alarm Type: {alarm_type} (Severity: {severity.upper()})
Command:    {command}
Confidence: {confidence} RAG match
Reasoning:  {reasoning}

⏱️ This request expires in 15 minutes.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ APPROVE (execute the fix):
{approve_url}

❌ DENY (cancel and log):
{deny_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OpsGuardian Autonomous SRE Agent
    """

    sns.publish(
        TopicArn=SNS_TOPIC,
        Subject=f"🚨 OpsGuardian: Approval Required — {alarm_type} on {instance_id}",
        Message=message
    )
    print(f"Approval email sent for incident {incident_id}")

    # Return the event — Step Functions will pause here waiting for callback
    return {
        **event,
        'approval_id': approval_id,
        'status': 'WaitingForApproval'
    }