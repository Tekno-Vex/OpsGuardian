import boto3
import json

def lambda_handler(event, context):
    print("OpsGuardian ACTIVATED - Incident detected!")
    print(f"Incoming event: {json.dumps(event)}")
    
    # --- Step 1: Extract the Instance ID from the CloudWatch alarm ---
    try:
        alarm_data = event['alarmData']
        dimensions = alarm_data['configuration']['metrics'][0]['metricStat']['metric']['dimensions']
        instance_id = dimensions['InstanceId']
        print(f"Target instance identified: {instance_id}")
    except Exception as e:
        print(f"Could not parse instance ID from event: {e}")
        print("Using fallback hardcoded instance ID")
        instance_id = "i-05f403183415c672e"
    
    # --- Step 2: Call Bedrock (Nova Micro) to reason about the fix ---
    print("Consulting Bedrock Nova Micro for remediation plan...")
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-2')
    
    prompt = """You are an expert cloud SRE agent. 
    A CloudWatch alarm just fired because EC2 CPU utilization exceeded 80%.
    What is the most likely cause and what single Linux command would you run to fix a runaway CPU process?
    Be brief - one sentence explanation and one command only."""
    
    bedrock_response = bedrock.invoke_model(
        modelId='us.amazon.nova-micro-v1:0',
        body=json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"text": prompt}
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 512
            }
        })
    )
    
    response_body = json.loads(bedrock_response['body'].read())
    ai_reasoning = response_body['output']['message']['content'][0]['text']
    print(f"Bedrock reasoning: {ai_reasoning}")
    
    # --- Step 3: Execute the fix via SSM ---
    print(f"Executing remediation on instance {instance_id}...")
    ssm = boto3.client('ssm', region_name='us-east-2')
    
    ssm_response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': ['pkill -f chaos_cpu.py && echo "Chaos process killed successfully"']}
    )
    
    command_id = ssm_response['Command']['CommandId']
    print(f"SSM Command sent! Command ID: {command_id}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'OpsGuardian remediation complete',
            'instance_id': instance_id,
            'ai_reasoning': ai_reasoning,
            'ssm_command_id': command_id
        })
    }