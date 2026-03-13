import boto3
import json
import uuid
import re
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
REGION          = 'us-east-2'
S3_BUCKET       = 'opsguardian-knowledge-base-856567377240'   # e.g. opsguardian-knowledge-base-856567377240
S3_KEY          = 'runbook.json'
DYNAMO_TABLE    = 'OpsGuardian_State'
FALLBACK_ID     = 'i-05f403183415c672e'   # e.g. i-05f403183415c672e
MODEL_ID        = 'us.amazon.nova-micro-v1:0'

# Critic blocklist - commands that must NEVER run
BLOCKLIST = [
    'rm -rf /',
    'rm -rf ~',
    'mkfs',
    'dd if=/dev/zero',
    ':(){:|:&};:',
    'chmod -R 777 /',
    '> /dev/sda'
]

# ── AWS CLIENTS ──────────────────────────────────────────────────────────────
s3       = boto3.client('s3',              region_name=REGION)
bedrock  = boto3.client('bedrock-runtime', region_name=REGION)
ssm      = boto3.client('ssm',             region_name=REGION)
dynamo   = boto3.resource('dynamodb',      region_name=REGION)

def lambda_handler(event, context):
    print("=" * 60)
    print("OpsGuardian ACTIVATED - Incident detected!")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")

    incident_id = str(uuid.uuid4())
    print(f"Incident ID: {incident_id}")

    # ── STEP 1: Parse Instance ID ─────────────────────────────────────────
    try:
        # When triggered via SNS, the CloudWatch event is nested inside SNS
        if 'Records' in event:
            sns_message = json.loads(event['Records'][0]['Sns']['Message'])
            dimensions  = sns_message['Trigger']['Dimensions']
            instance_id = next(d['value'] for d in dimensions if d['name'] == 'InstanceId')
        else:
            dimensions  = event['alarmData']['configuration']['metrics'][0]['metricStat']['metric']['dimensions']
            instance_id = dimensions['InstanceId']
        print(f"Target instance: {instance_id}")
    except Exception as e:
        print(f"Could not parse instance ID ({e}), using fallback")
        instance_id = FALLBACK_ID

    # ── STEP 2: Determine Alarm Type ──────────────────────────────────────
    alarm_type = "HighCPU"   # We know this from Sprint 1 setup
    print(f"Alarm type: {alarm_type}")

    # ── STEP 3: Investigator - Fetch Runbook from S3 ──────────────────────
    print(f"Fetching runbook from S3: s3://{S3_BUCKET}/{S3_KEY}")
    try:
        s3_response = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        runbook     = json.loads(s3_response['Body'].read().decode('utf-8'))
        print(f"Runbook loaded: {json.dumps(runbook)}")
    except Exception as e:
        print(f"ERROR fetching runbook: {e}")
        log_to_dynamo(incident_id, instance_id, alarm_type, "ERROR", str(e), "N/A", "Failed")
        raise

    # ── STEP 4: Architect - Ask Bedrock to pick the right command ─────────
    print("Consulting Bedrock Nova Micro...")
    prompt = f"""You are an expert AWS SRE agent. 
An alarm of type '{alarm_type}' has fired on instance '{instance_id}'.
Here is the runbook of known fixes:
{json.dumps(runbook, indent=2)}

Based ONLY on the runbook above, what is the single exact shell command to fix a '{alarm_type}' alarm?
Rules:
- Output ONLY the raw command, nothing else
- No explanation, no markdown, no backticks
- Just the command itself"""

    try:
        bedrock_response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {"maxTokens": 100}
            })
        )
        response_body = json.loads(bedrock_response['body'].read())
        raw_command   = response_body['output']['message']['content'][0]['text'].strip()
        print(f"Bedrock proposed command: '{raw_command}'")
    except Exception as e:
        print(f"ERROR calling Bedrock: {e}")
        log_to_dynamo(incident_id, instance_id, alarm_type, "ERROR", str(e), "N/A", "Failed")
        raise

    # ── STEP 5: Critic - Safety Check ─────────────────────────────────────
    print("Running Critic safety check...")
    for blocked in BLOCKLIST:
        if blocked in raw_command:
            msg = f"CRITIC BLOCKED unsafe command: '{raw_command}' contains '{blocked}'"
            print(msg)
            log_to_dynamo(incident_id, instance_id, alarm_type, raw_command, "Blocked by Critic", "N/A", "Blocked")
            raise Exception(msg)
    print("Critic approved the command ✓")

    # ── STEP 6: Execute via SSM ───────────────────────────────────────────
    print(f"Executing on instance {instance_id}: {raw_command}")
    try:
        ssm_response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [raw_command]}
        )
        command_id = ssm_response['Command']['CommandId']
        print(f"SSM Command sent! ID: {command_id}")
        status = "Resolved"
    except Exception as e:
        print(f"ERROR executing SSM command: {e}")
        command_id = "N/A"
        status     = "Failed"

    # ── STEP 7: Learning Element - Log to DynamoDB ────────────────────────
    reasoning = f"Detected {alarm_type} on {instance_id}. Runbook suggested: '{raw_command}'. Critic approved. SSM executed."
    log_to_dynamo(incident_id, instance_id, alarm_type, raw_command, reasoning, command_id, status)

    print("=" * 60)
    print(f"OpsGuardian cycle complete. Status: {status}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'incident_id':  incident_id,
            'instance_id':  instance_id,
            'alarm_type':   alarm_type,
            'command':      raw_command,
            'ssm_command':  command_id,
            'status':       status
        })
    }


def log_to_dynamo(incident_id, instance_id, alarm_type, command, reasoning, command_id, status):
    """Write incident record to DynamoDB"""
    try:
        table = dynamo.Table(DYNAMO_TABLE)
        table.put_item(Item={
            'incident_id':  incident_id,
            'timestamp':    datetime.utcnow().isoformat(),
            'instance_id':  instance_id,
            'alarm_type':   alarm_type,
            'command':      command,
            'reasoning':    reasoning,
            'ssm_command_id': command_id,
            'status':       status
        })
        print(f"Logged to DynamoDB: incident {incident_id} → {status}")
    except Exception as e:
        print(f"ERROR writing to DynamoDB: {e}")