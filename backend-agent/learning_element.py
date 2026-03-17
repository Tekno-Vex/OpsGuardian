import boto3
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal

REGION       = 'us-east-2'
DYNAMO_TABLE = 'OpsGuardian_State'
S3_BUCKET    = os.environ.get('S3_BUCKET', 'YOUR-BUCKET-NAME-HERE')
SNS_TOPIC    = os.environ.get('SNS_TOPIC_ARN', '')
MODEL_ID     = 'us.amazon.nova-micro-v1:0'

dynamo  = boto3.resource('dynamodb', region_name=REGION)
s3      = boto3.client('s3',              region_name=REGION)
bedrock = boto3.client('bedrock-runtime', region_name=REGION)
sns     = boto3.client('sns',             region_name=REGION)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def get_bedrock_suggestions(alarm_type, command, success_rate, sample_size):
    """Ask Nova Micro to suggest better alternative commands"""
    prompt = f"""You are an expert Linux SRE engineer analyzing command effectiveness.

The command '{command}' was used to fix '{alarm_type}' incidents.
It only worked {success_rate*100:.1f}% of the time across {sample_size} incidents.

Please suggest exactly 3 alternative Linux shell commands that would be more reliable for fixing '{alarm_type}'.
Also explain in one sentence why '{command}' might be failing.

Respond in this EXACT JSON format with no other text:
{{
  "alternatives": ["command1", "command2", "command3"],
  "reasoning": "One sentence explanation of why the current command fails"
}}"""

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
                "inferenceConfig": {"maxTokens": 300}
            })
        )
        body = json.loads(response['body'].read())
        text = body['output']['message']['content'][0]['text'].strip()

        # Clean up response — remove markdown if present
        text = text.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(text)

        return {
            'alternatives': parsed.get('alternatives', []),
            'reasoning':    parsed.get('reasoning', 'No reasoning provided')
        }
    except Exception as e:
        print(f"Bedrock error: {e}")
        return {
            'alternatives': [
                f"sudo systemctl restart {alarm_type.lower()}",
                f"kill -9 $(pgrep -f {command.split()[-1]})",
                "sudo reboot"
            ],
            'reasoning': f"Could not get AI suggestions: {str(e)}"
        }

def lambda_handler(event, context):
    print("=" * 60)
    print(f"OpsGuardian Learning Element activated")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")

    today      = datetime.utcnow()
    week_ago   = today - timedelta(days=7)
    date_str   = today.strftime('%Y-%m-%d')

    # ── STEP 1: Scan DynamoDB for last 7 days ────────────────
    print(f"Scanning DynamoDB for incidents since {week_ago.isoformat()}")
    table    = dynamo.Table(DYNAMO_TABLE)
    response = table.scan()
    all_items = response.get('Items', [])

    # Filter to last 7 days and exclude LOCK# rows
    recent_items = []
    for item in all_items:
        if str(item.get('incident_id', '')).startswith('LOCK#'):
            continue
        ts = item.get('timestamp', '')
        if ts:
            try:
                item_time = datetime.fromisoformat(ts)
                if item_time >= week_ago:
                    recent_items.append(item)
            except:
                pass

    print(f"Found {len(recent_items)} incidents in last 7 days")

    if not recent_items:
        print("No recent incidents — nothing to analyze")
        return {'statusCode': 200, 'body': 'No incidents to analyze'}

    # ── STEP 2: Group by command and compute success rates ───
    command_stats = defaultdict(lambda: {
        'total': 0, 'success': 0, 'alarm_types': set(), 'failures': 0
    })

    for item in recent_items:
        cmd    = item.get('command', '')
        status = item.get('status', '')
        alarm  = item.get('alarm_type', 'Unknown')

        if not cmd or cmd in ('none', 'unknown', 'N/A', ''):
            continue

        command_stats[cmd]['total']  += 1
        command_stats[cmd]['alarm_types'].add(alarm)

        outcome = item.get('command_outcome', '')
        if outcome == 'success' or status == 'Resolved':
            command_stats[cmd]['success'] += 1
        else:
            command_stats[cmd]['failures'] += 1

    print(f"Analyzed {len(command_stats)} unique commands")

    # ── STEP 3: Find underperforming commands ────────────────
    underperforming = []
    performing_well = []

    for cmd, stats in command_stats.items():
        if stats['total'] == 0:
            continue
        rate = stats['success'] / stats['total']
        alarm_type = list(stats['alarm_types'])[0] if stats['alarm_types'] else 'Unknown'

        entry = {
            'command':    cmd,
            'alarm_type': alarm_type,
            'total':      stats['total'],
            'success':    stats['success'],
            'rate':       round(rate, 4)
        }

        if rate < 0.50:
            underperforming.append(entry)
            print(f"UNDERPERFORMING: '{cmd}' → {rate*100:.1f}% ({stats['success']}/{stats['total']})")
        else:
            performing_well.append(entry)
            print(f"PERFORMING WELL: '{cmd}' → {rate*100:.1f}% ({stats['success']}/{stats['total']})")

    # ── STEP 4: Generate AI suggestions for failing commands ─
    suggestions = []

    if underperforming:
        print(f"\nGenerating AI suggestions for {len(underperforming)} underperforming commands...")
        for entry in underperforming:
            print(f"Asking Bedrock for alternatives to '{entry['command']}'...")
            ai_result = get_bedrock_suggestions(
                entry['alarm_type'],
                entry['command'],
                entry['rate'],
                entry['total']
            )

            suggestions.append({
                'alarm_type':            entry['alarm_type'],
                'current_command':       entry['command'],
                'success_rate':          entry['rate'],
                'sample_size':           entry['total'],
                'suggested_alternatives': ai_result['alternatives'],
                'bedrock_reasoning':     ai_result['reasoning']
            })
    else:
        print("All commands performing well — generating positive report")

    # ── STEP 5: Build the report ─────────────────────────────
    well_performing_summary = [
        {
            'command':      e['command'],
            'alarm_type':   e['alarm_type'],
            'success_rate': e['rate'],
            'sample_size':  e['total']
        }
        for e in performing_well
    ]

    report = {
        'generated_at':        date_str,
        'analysis_period':     f"{week_ago.strftime('%Y-%m-%d')} to {date_str}",
        'total_incidents':     len(recent_items),
        'commands_analyzed':   len(command_stats),
        'underperforming':     len(underperforming),
        'suggestions':         suggestions,
        'performing_well':     well_performing_summary,
        'recommendation':      'Review and apply suggested alternatives to improve remediation reliability' if suggestions else 'All commands performing well — no changes needed'
    }

    # ── STEP 6: Write to S3 ───────────────────────────────────
    s3_key = f"pending_updates/{date_str}.json"
    print(f"\nWriting report to S3: s3://{S3_BUCKET}/{s3_key}")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(report, indent=2, cls=DecimalEncoder),
        ContentType='application/json'
    )
    print(f"Report written successfully!")

    # ── STEP 7: Send SNS notification ────────────────────────
    s3_url = f"https://s3.console.aws.amazon.com/s3/object/{S3_BUCKET}?prefix={s3_key}"

    if suggestions:
        subject = f"🧠 OpsGuardian: {len(suggestions)} Runbook Improvement(s) Suggested — {date_str}"
        message = f"""
OpsGuardian Learning Element — Weekly Analysis Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analysis Period: {report['analysis_period']}
Total Incidents Analyzed: {len(recent_items)}
Commands Analyzed: {len(command_stats)}
Underperforming Commands: {len(underperforming)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUGGESTED IMPROVEMENTS:
"""
        for s in suggestions:
            message += f"""
Command: {s['current_command']}
Alarm Type: {s['alarm_type']}
Current Success Rate: {s['success_rate']*100:.1f}% ({s['sample_size']} incidents)
AI Reasoning: {s['bedrock_reasoning']}
Suggested Alternatives:
"""
            for i, alt in enumerate(s['suggested_alternatives'], 1):
                message += f"  {i}. {alt}\n"

        message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Review full report: {s3_url}

To apply improvements:
1. Review the suggestions above
2. Update knowledge-base/runbook_rich.json locally
3. Run python build_embeddings.py to regenerate vectors
4. Upload new embeddings.json to S3

OpsGuardian Autonomous SRE Agent
"""
    else:
        subject = f"✅ OpsGuardian: All Commands Performing Well — {date_str}"
        message = f"""
OpsGuardian Learning Element — Weekly Analysis Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analysis Period: {report['analysis_period']}
Total Incidents: {len(recent_items)}
Commands Analyzed: {len(command_stats)}

All commands are performing above the 50% success threshold.
No runbook changes recommended this week.

Full report: {s3_url}

OpsGuardian Autonomous SRE Agent
"""

    if SNS_TOPIC:
        sns.publish(
            TopicArn=SNS_TOPIC,
            Subject=subject,
            Message=message
        )
        print(f"SNS notification sent!")
    else:
        print("No SNS topic configured — skipping notification")

    print("=" * 60)
    print(f"Learning Element complete. Suggestions generated: {len(suggestions)}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'date':              date_str,
            'incidents_analyzed': len(recent_items),
            'suggestions':       len(suggestions),
            's3_report':         s3_key
        })
    }