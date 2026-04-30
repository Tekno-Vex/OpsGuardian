"""OpsGuardian — Watcher Agent
============================
Entry point for the OpsGuardian pipeline.
Triggered by SNS when a CloudWatch alarm fires.
Parses the alarm event to extract instance ID and alarm type,
then starts the AWS Step Functions state machine execution.
"""

import boto3
import json
import uuid
import os
from datetime import datetime

REGION        = 'us-east-2'
STATE_MACHINE = os.environ.get('STATE_MACHINE_ARN', 'PLACEHOLDER')
FALLBACK_ID   = 'i-05f403183415c672e'

sfn = boto3.client('stepfunctions', region_name=REGION)

def lambda_handler(event, context):
    print(f"Watcher activated. Event: {json.dumps(event)}")
    try:
        if 'Records' in event:
            sns_message = json.loads(event['Records'][0]['Sns']['Message'])
            dimensions  = sns_message['Trigger']['Dimensions']
            instance_id = next(d['value'] for d in dimensions if d['name'] == 'InstanceId')
            alarm_name  = sns_message.get('AlarmName', 'Unknown')
        else:
            dimensions  = event['alarmData']['configuration']['metrics'][0]['metricStat']['metric']['dimensions']
            instance_id = dimensions['InstanceId']
            alarm_name  = event.get('alarmData', {}).get('alarmName', 'Unknown')
    except Exception as e:
        print(f"Could not parse event ({e}), using fallback")
        instance_id = FALLBACK_ID
        alarm_name  = 'OpsGuardian-HighCPU-Alarm'
    alarm_name_lower = alarm_name.lower()
    if 'memory' in alarm_name_lower or 'mem' in alarm_name_lower:
        alarm_type = 'HighMemory'
    elif 'disk' in alarm_name_lower or 'storage' in alarm_name_lower:
        alarm_type = 'DiskFull'
    elif 'network' in alarm_name_lower or 'timeout' in alarm_name_lower:
        alarm_type = 'NetworkTimeout'
    elif 'crash' in alarm_name_lower or 'process' in alarm_name_lower:
        alarm_type = 'ProcessCrash'
    else:
        alarm_type = 'HighCPU'

    print(f"Alarm: {alarm_name} → Type: {alarm_type} → Instance: {instance_id}")

    incident = {
        'incident_id':      str(uuid.uuid4()),
        'timestamp':        datetime.utcnow().isoformat(),
        'instance_id':      instance_id,
        'alarm_name':       alarm_name,
        'alarm_type':       alarm_type,
        'status':           'InProgress',
        'runbook':          {},
        'proposed_command': '',
        'critic_approved':  False,
        'critic_reason':    '',
        'ssm_command_id':   '',
        'reasoning':        ''
    }

    print(f"Starting pipeline for incident {incident['incident_id']}")
    sfn.start_execution(
        stateMachineArn=STATE_MACHINE,
        name=f"incident-{incident['incident_id']}",
        input=json.dumps(incident)
    )

    return {'statusCode': 200, 'body': 'Pipeline started'}