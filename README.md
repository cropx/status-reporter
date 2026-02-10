# QA Status Reporter

Automated daily status reporter for QA Dev namespace that sends reports to RabbitMQ.

## Features

- Monitors all pods in the `dev` namespace
- Categorizes pods: Critical (CrashLoopBackOff), Warnings (high restarts), Healthy
- Calculates health score
- Sends report to RabbitMQ exchange `device_raw_data_exchange`
- Runs daily at 8:00 AM UTC via Kubernetes CronJob

## Message Format

The report is sent to RabbitMQ in the following format:

```json
{
  "message": "<JSON string of the report>",
  "source": "QA_LIVE"
}
```

## Report Structure

```json
{
  "timestamp": "2026-02-10T08:00:00Z",
  "namespace": "dev",
  "environment": "QA",
  "summary": {
    "total_pods": 100,
    "healthy": 90,
    "warnings": 6,
    "critical": 4,
    "health_score": 90
  },
  "critical_issues": [
    {"name": "data-transport-service-xxx", "status": "CrashLoopBackOff", "restarts": 612}
  ],
  "warnings": [
    {"name": "davis-data-handler-xxx", "status": "Running", "restarts": 453}
  ],
  "healthy_count": 90
}
```

## Deployment

### 1. Build and Push Docker Image

```bash
cd /Users/michael/workspace/status-reporter
chmod +x deploy.sh
./deploy.sh
```

### 2. Manual Test

Test the reporter manually before scheduling:

```bash
# Create a one-time job from the cronjob
kubectl create job --from=cronjob/status-reporter test-run-1 -n dev

# Watch the job
kubectl get jobs -n dev -w

# Check logs
kubectl logs -n dev -l app=status-reporter --tail=100
```

### 3. Verify CronJob

```bash
# Check cronjob status
kubectl get cronjob status-reporter -n dev

# View schedule
kubectl describe cronjob status-reporter -n dev
```

## Configuration

Edit `cronjob.yaml` to change:

- **Schedule**: Modify `schedule: "0 8 * * *"` (cron format)
  - Current: Daily at 8:00 AM UTC
  - Examples:
    - `"0 */6 * * *"` - Every 6 hours
    - `"0 0,12 * * *"` - Twice daily (midnight and noon)
    - `"0 8 * * 1-5"` - Weekdays only at 8 AM

- **RabbitMQ Exchange**: Modify `RABBITMQ_EXCHANGE` in ConfigMap

- **Resource Limits**: Adjust `resources` section

## Monitoring

```bash
# View recent jobs
kubectl get jobs -n dev | grep status-reporter

# View cronjob history
kubectl get cronjob status-reporter -n dev -o yaml

# Delete old jobs manually if needed
kubectl delete job <job-name> -n dev
```

## Troubleshooting

```bash
# Check if ServiceAccount has permissions
kubectl auth can-i get pods --as=system:serviceaccount:dev:status-reporter -n dev

# Check RabbitMQ secret
kubectl get secret rabitmq-cluster-default-user -n dev

# Test connectivity to RabbitMQ from a pod
kubectl run -it --rm debug --image=python:3.11-slim --restart=Never -n dev -- bash
```

## Files

- `status_reporter.py` - Main Python script
- `Dockerfile` - Container image definition  
- `cronjob.yaml` - Kubernetes CronJob manifest
- `deploy.sh` - Build and deployment script
- `README.md` - This file
