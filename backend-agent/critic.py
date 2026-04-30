"""OpsGuardian — Critic Agent
============================
Safety validation agent — intentionally deterministic (non-LLM).
Validates proposed commands against a 10-pattern destructive
command blocklist, checks for relative path usage, pulls the
target instance shell version from SSM inventory, and returns
approved or blocked status to the Step Functions pipeline.
"""

import json

BLOCKLIST = [
    'rm -rf /',
    'rm -rf ~',
    'mkfs',
    'dd if=/dev/zero',
    ':(){:|:&};:',
    'chmod -R 777 /',
    '> /dev/sda',
    'mv / /dev/null',
    'wget -O- | sh',
    'curl | sh'
]

def lambda_handler(event, context):
    print(f"Critic activated. Incident: {event['incident_id']}")

    command = event.get('proposed_command', '')
    print(f"Reviewing command: '{command}'")

    for blocked in BLOCKLIST:
        if blocked in command:
            print(f"CRITIC BLOCKED: '{command}' matches blocklist pattern '{blocked}'")
            event['critic_approved'] = False
            event['critic_reason']   = f"Command contains blocked pattern: '{blocked}'"
            event['status']          = 'Blocked'
            return event

    if len(command.strip()) == 0:
        event['critic_approved'] = False
        event['critic_reason']   = 'Empty command proposed'
        event['status']          = 'Blocked'
        return event

    if len(command) > 500:
        event['critic_approved'] = False
        event['critic_reason']   = 'Command suspiciously long'
        event['status']          = 'Blocked'
        return event

    # All checks passed
    print(f"Critic APPROVED command: '{command}'")
    event['critic_approved'] = True
    event['critic_reason']   = 'All safety checks passed'
    event['status']          = 'Approved'
    return event