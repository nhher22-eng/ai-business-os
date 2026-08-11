#!/usr/bin/env bash
set -euo pipefail

UNIT="${1:-unknown}"
HOST="$(hostname)"
NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

SNS_TOPIC_ARN="arn:aws:sns:ap-northeast-2:670079394284:ai-business-os-alerts"
AWS_REGION="ap-northeast-2"

MESSAGE="AI Business OS ALERT: health check failed | host=${HOST} | unit=${UNIT} | time=${NOW}"

logger -p user.err -t aios-alert "$MESSAGE"
echo "$MESSAGE"

if command -v aws >/dev/null 2>&1; then
    if ! aws sns publish \
        --region "$AWS_REGION" \
        --topic-arn "$SNS_TOPIC_ARN" \
        --subject "AI Business OS Production Alert" \
        --message "$MESSAGE" >/dev/null; then
        logger -p user.err -t aios-alert "SNS publish failed for unit=${UNIT}"
        echo "WARNING: SNS publish failed" >&2
    fi
else
    logger -p user.err -t aios-alert "AWS CLI unavailable; SNS alert not sent"
    echo "WARNING: AWS CLI unavailable; SNS alert not sent" >&2
fi
