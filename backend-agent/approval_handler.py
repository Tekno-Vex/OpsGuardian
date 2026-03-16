import boto3
import json
from datetime import datetime
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

REGION              = 'us-east-2'
APPROVALS_TABLE     = 'OpsGuardian_PendingApprovals'
STATE_TABLE         = 'OpsGuardian_State'

dynamo = boto3.resource('dynamodb', region_name=REGION)
sfn    = boto3.client('stepfunctions', region_name=REGION)

def make_html(title, message, color, emoji):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OpsGuardian — {title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: #0d0d1a;
            color: #e0e0e0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #1e1e2e;
            border: 2px solid {color};
            border-radius: 16px;
            padding: 48px;
            text-align: center;
            max-width: 500px;
            box-shadow: 0 0 40px {color}44;
        }}
        .emoji {{ font-size: 64px; margin-bottom: 16px; }}
        h1 {{ color: {color}; margin: 0 0 16px; font-size: 28px; }}
        p {{ color: #aaa; line-height: 1.6; }}
        .badge {{
            display: inline-block;
            background: {color}22;
            border: 1px solid {color};
            color: {color};
            padding: 4px 16px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 16px;
            letter-spacing: 2px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="emoji">{emoji}</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <div class="badge">OPSGUARDIAN AUTONOMOUS SRE</div>
    </div>
</body>
</html>
"""

def lambda_handler(event, context):
    print(f"ApprovalHandler activated. Event: {json.dumps(event)}")

    # Extract path parameters from API Gateway
    path_params = event.get('pathParameters', {})
    approval_id = path_params.get('approval_id')
    decision    = path_params.get('decision', '').lower()

    print(f"Approval ID: {approval_id}, Decision: {decision}")

    if not approval_id or decision not in ['approve', 'deny']:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'text/html'},
            'body': make_html(
                'Invalid Request',
                'Missing or invalid approval ID or decision.',
                '#ff6d00', '⚠️'
            )
        }

    # Fetch approval record from DynamoDB
    approvals_table = dynamo.Table(APPROVALS_TABLE)
    try:
        response = approvals_table.get_item(Key={'approval_id': approval_id})
        item     = response.get('Item')
    except Exception as e:
        print(f"DynamoDB error: {e}")
        item = None

    if not item:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'text/html'},
            'body': make_html(
                'Request Expired',
                'This approval request has already been actioned or has expired.',
                '#ff6d00', '⏱️'
            )
        }

    task_token  = item['task_token']
    command     = item.get('command', 'unknown')
    alarm_type  = item.get('alarm_type', 'unknown')
    instance_id = item.get('instance_id', 'unknown')

    # Delete from DynamoDB immediately — prevent double-clicks
    approvals_table.delete_item(Key={'approval_id': approval_id})

    if decision == 'approve':
        print(f"APPROVED — resuming Step Functions execution")
        try:
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    **item,
                    'proposed_command': item.get('command', ''),
                    'human_decision': 'approved',
                    'decision_time':  datetime.utcnow().isoformat(),
                    'status':         'ApprovedByHuman'
                }, cls=DecimalEncoder)
            )
        except Exception as e:
            print(f"Error resuming Step Functions: {e}")

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': make_html(
                'Fix Approved!',
                f'OpsGuardian is now executing the fix on <strong>{instance_id}</strong>.<br><br>'
                f'Command: <code style="background:#2a2a3e;padding:4px 8px;border-radius:4px">{command}</code><br><br>'
                f'Check the Step Functions dashboard to watch it execute.',
                '#00c853', '✅'
            )
        }

    else:  # deny
        print(f"DENIED — cancelling Step Functions execution")
        try:
            sfn.send_task_failure(
                taskToken=task_token,
                error='HumanDenied',
                cause=json.dumps({
                    'reason': f'Fix denied by on-call engineer at {datetime.utcnow().isoformat()}'
                }, cls=DecimalEncoder)
            )
        except Exception as e:
            print(f"Error cancelling Step Functions: {e}")

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': make_html(
                'Fix Denied',
                f'The proposed fix on <strong>{instance_id}</strong> has been cancelled.<br><br>'
                f'Incident has been logged. Manual investigation required.',
                '#ff1744', '❌'
            )
        }