"""OpsGuardian — Architect Agent
===============================
Goal-Based Agent responsible for LLM reasoning.
Receives the matched runbook entry and RAG confidence score,
constructs a structured prompt, and calls Amazon Bedrock Nova Micro
to determine the exact shell command needed for remediation.
"""

import boto3
import json

REGION   = 'us-east-2'
MODEL_ID = 'us.amazon.nova-micro-v1:0'

bedrock = boto3.client('bedrock-runtime', region_name=REGION)

def lambda_handler(event, context):
    print(f"Architect activated. Incident: {event['incident_id']}")

    alarm_type  = event['alarm_type']
    instance_id = event['instance_id']
    runbook     = event['runbook']

    prompt = f"""You are an expert AWS SRE agent.
An alarm of type '{alarm_type}' has fired on instance '{instance_id}'.

Here is the complete runbook of known fixes:
{json.dumps(runbook, indent=2)}

Your task: Return ONLY the single exact shell command to fix a '{alarm_type}' alarm.
Rules:
- Output ONLY the raw shell command
- No explanation, no markdown, no backticks, no punctuation
- Just the command itself on a single line"""

    try:
        response = bedrock.invoke_model(
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

        body            = json.loads(response['body'].read())
        proposed_command = body['output']['message']['content'][0]['text'].strip()

        print(f"Bedrock proposed command: '{proposed_command}'")

        event['proposed_command'] = proposed_command
        event['reasoning']        = f"Detected {alarm_type} on {instance_id}. Runbook suggested: '{proposed_command}'."
        event['status']           = 'CommandProposed'
        return event

    except Exception as e:
        print(f"ERROR calling Bedrock: {e}")
        event['status'] = 'BedrockFailed'
        event['error']  = str(e)
        raise Exception(f"Architect failed: {str(e)}")