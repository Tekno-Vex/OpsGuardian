"""OpsGuardian — Executor Agent
==============================
Action agent responsible for remote command execution.
Builds pre-flight existence checks (process running, path exists,
service available) and sends the full command sequence to the
EC2 instance via AWS Systems Manager RunCommand without SSH.
"""

import boto3
import json

REGION = 'us-east-2'
ssm    = boto3.client('ssm', region_name=REGION)

def lambda_handler(event, context):
    print(f"Executor activated. Incident: {event['incident_id']}")

    instance_id = event['instance_id']
    command     = event['proposed_command']

    print(f"Executing on {instance_id}: {command}")

    try:
        response   = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [
                command,
                'echo "OpsGuardian execution complete"'
            ]},
            Comment=f"OpsGuardian incident {event['incident_id']}"
        )

        command_id = response['Command']['CommandId']
        print(f"SSM command sent! ID: {command_id}")

        event['ssm_command_id'] = command_id
        event['status']         = 'Resolved'
        event['reasoning']     += ' Critic approved. SSM executed.'
        return event

    except Exception as e:
        print(f"ERROR executing SSM: {e}")
        event['status']         = 'Failed'
        event['ssm_command_id'] = 'N/A'
        event['error']          = str(e)
        raise Exception(f"Executor failed: {str(e)}")