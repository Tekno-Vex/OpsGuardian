import boto3
import json
import os

REGION    = 'us-east-2'
S3_BUCKET = os.environ.get('S3_BUCKET', 'opsguardian-knowledge-base-856567377240')
S3_KEY    = 'runbook.json'

s3 = boto3.client('s3', region_name=REGION)

def lambda_handler(event, context):
    print(f"Investigator activated. Incident: {event['incident_id']}")

    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        runbook  = json.loads(response['Body'].read().decode('utf-8'))
        print(f"Runbook loaded successfully: {list(runbook.keys())}")

        event['runbook'] = runbook
        event['status']  = 'RunbookLoaded'
        return event

    except Exception as e:
        print(f"ERROR loading runbook: {e}")
        event['status'] = 'RunbookLoadFailed'
        event['error']  = str(e)
        raise Exception(f"Investigator failed: {str(e)}")