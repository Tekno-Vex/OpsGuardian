import boto3
import json
from boto3.dynamodb.conditions import Key
from decimal import Decimal

REGION      = 'us-east-2'
DYNAMO_TABLE = 'OpsGuardian_State'

dynamo = boto3.resource('dynamodb', region_name=REGION)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,OPTIONS'
    }

    try:
        table    = dynamo.Table(DYNAMO_TABLE)
        response = table.scan()
        items    = response.get('Items', [])

        # Sort by timestamp descending — newest first
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Build a clean summary
        latest        = items[0] if items else None
        total         = len(items)
        resolved      = sum(1 for i in items if i.get('status') == 'Resolved')
        failed        = sum(1 for i in items if i.get('status') == 'Failed')
        blocked       = sum(1 for i in items if i.get('status') == 'Blocked')

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'system_status': latest.get('status', 'Unknown') if latest else 'Healthy',
                'latest_incident': latest,
                'all_incidents': items[:10],  # Return last 10
                'stats': {
                    'total':    total,
                    'resolved': resolved,
                    'failed':   failed,
                    'blocked':  blocked
                }
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }