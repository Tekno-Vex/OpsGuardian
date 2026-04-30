"""OpsGuardian — Logger Agent
============================
Learning agent and audit trail recorder.
Always executes regardless of pipeline outcome (success, failure,
blocked, denied). Writes the complete incident record to DynamoDB
including command, reasoning, RAG match, shell version,
preflight checks, and final status.
"""

import boto3
import json
from datetime import datetime

REGION       = 'us-east-2'
DYNAMO_TABLE = 'OpsGuardian_State'

dynamo = boto3.resource('dynamodb', region_name=REGION)

def lambda_handler(event, context):
    print(f"Logger activated. Incident: {event.get('incident_id', 'unknown')}")

    if 'Error' in event and 'incident_id' not in event:
        incident_id = 'error-' + datetime.utcnow().isoformat()
        item = {
            'incident_id':    incident_id,
            'timestamp':      datetime.utcnow().isoformat(),
            'instance_id':    'unknown',
            'alarm_type':     'unknown',
            'command':        'unknown',
            'reasoning':      f"Pipeline error: {event.get('Cause', 'unknown')}",
            'ssm_command_id': 'N/A',
            'status':         'PipelineError',
            'critic_approved': False
        }
    else:
        item = {
            'incident_id':    event.get('incident_id', 'unknown'),
            'timestamp':      event.get('timestamp', datetime.utcnow().isoformat()),
            'instance_id':    event.get('instance_id', 'unknown'),
            'alarm_type':     event.get('alarm_type', 'unknown'),
            'command':        event.get('proposed_command', 'none'),
            'reasoning':      event.get('reasoning', 'no reasoning captured'),
            'ssm_command_id': event.get('ssm_command_id', 'N/A'),
            'status':         event.get('status', 'Unknown'),
            'critic_approved': event.get('critic_approved', False),
            'critic_reason':   event.get('critic_reason', '')
        }

    try:
        table = dynamo.Table(DYNAMO_TABLE)
        table.put_item(Item=item)
        print(f"Logged to DynamoDB: {item['incident_id']} → {item['status']}")
    except Exception as e:
        print(f"ERROR writing to DynamoDB: {e}")

    return item