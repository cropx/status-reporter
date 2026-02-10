# QA Status Reporter

Automated daily status reporter for QA Dev namespace that sends markdown-formatted reports to RabbitMQ for Slack notifications.

**GitHub Repository:** https://github.com/cropx/status-reporter

## Features

- 🔍 Monitors all pods in the `dev` namespace on Kubernetes
- 📊 Categorizes pods: Critical (CrashLoopBackOff), Warnings (high restarts), Healthy
- 📈 Calculates health score (percentage)
- 📝 Formats report as **markdown** with emojis
- 📮 Sends to RabbitMQ queue `slack_send_message_queue`
- ⏰ Runs daily at 8:00 AM UTC via Kubernetes CronJob
- 🎯 Includes Slack channel ID for direct posting

## Message Format

The report is sent to RabbitMQ in the following format:

```json
{
  "message": "# 🟡 QA Environment Status Report\n\n**Environment:** QA\n...",
  "source": "QA_LIVE",
  "channel": "C0ADXA2FXH9"
}
```

**Fields:**
- `message` - Markdown-formatted health report (see example below)
- `source` - Source identifier (`QA_LIVE`)
- `channel` - Slack channel ID (`C0ADXA2FXH9`)

### Markdown Report Example

```markdown
# 🟡 QA Environment Status Report

**Environment:** QA  
**Namespace:** dev  
**Timestamp:** 2026-02-10T08:00:00.000000Z

## 📊 Summary

- **Health Score:** 93%
- **Total Pods:** 98
- **Healthy:** 92 ✅
- **Warnings:** 1 ⚠️
- **Critical:** 5 🔴

## 🔴 Critical Issues

- **data-transport-service-xyz**
  - Status: `CrashLoopBackOff`
  - Restarts: 15

## ⚠️ Warnings (High Restart Count)

- **davis-data-handler-ghi**
  - Status: `Running`
  - Restarts: 453

## ✅ Healthy Services

92 pods running normally
```

## Architecture

- **Language:** Python 3.11
- **Container Registry:** Google Artifact Registry (`us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/status-reporter`)
- **Kubernetes:** CronJob in `dev` namespace
- **RabbitMQ:** Queue `slack_send_message_queue` (using `GDS_service_QA` credentials)
- **Schedule:** `0 8 * * *` (Daily at 8:00 AM UTC)

## Deployment

### Prerequisites

- Access to jenkins-t375 server
- Kubernetes cluster credentials configured (`dev-kubernetes`)
- Docker authentication for Artifact Registry

### Option 1: Using Jenkins Pipeline (Recommended)

1. Create Jenkins job pointing to https://github.com/cropx/status-reporter
2. Use `Jenkinsfile.artifactregistry`
3. Run the pipeline with parameters:
   - `BRANCHGIT`: main
   - `RUN_TEST`: true (optional, for immediate testing)
   - `FORCE_REBUILD`: false

See [JENKINS.md](JENKINS.md) for detailed setup.

### Option 2: Manual Deployment

```bash
# Clone repository
git clone https://github.com/cropx/status-reporter.git
cd status-reporter

# Build Docker image
export FULL_IMAGE_NAME="us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/status-reporter"
docker build -t ${FULL_IMAGE_NAME}:qa-latest .

# Configure Docker for Artifact Registry
gcloud auth configure-docker us-east4-docker.pkg.dev --quiet

# Push to registry
docker push ${FULL_IMAGE_NAME}:qa-latest

# Deploy to Kubernetes
kubectl apply -f cronjob-artifactregistry.yaml

# Verify deployment
kubectl get cronjob status-reporter -n dev
```

### Manual Test

Test the reporter manually before waiting for scheduled run:

```bash
# Create a one-time job from the cronjob
kubectl create job --from=cronjob/status-reporter test-manual -n dev

# Watch the job
kubectl get pods -n dev -l app=status-reporter -w

# Check logs
kubectl logs -n dev -l app=status-reporter --tail=100

# Verify message in RabbitMQ
kubectl exec -n dev rabitmq-cluster-server-0 -- \
  rabbitmqctl list_queues name messages | grep slack_send_message_queue
```

## Configuration

### RabbitMQ Settings

Configured via ConfigMap `status-reporter-config`:

```yaml
RABBITMQ_HOST: "rabitmq-cluster"
RABBITMQ_PORT: "5672"
RABBITMQ_QUEUE: "slack_send_message_queue"
RABBITMQ_USER: "GDS_service_QA"
```

Password retrieved from secret `rabbitmq-gds-qa`.

### Schedule

Edit `cronjob-artifactregistry.yaml` to change schedule:

- **Current:** `"0 8 * * *"` - Daily at 8:00 AM UTC
- **Examples:**
  - `"0 */6 * * *"` - Every 6 hours
  - `"0 0,12 * * *"` - Twice daily (midnight and noon)
  - `"0 8 * * 1-5"` - Weekdays only at 8 AM

### Health Thresholds

Modify in `status_reporter.py`:

```python
# Critical: Pods in CrashLoopBackOff
if 'CrashLoopBackOff' in status:
    critical.append(...)

# Warnings: Restarts > 100
elif restarts > 100:
    warnings.append(...)
```

## Monitoring

### View CronJob Status

```bash
# Check cronjob
kubectl get cronjob status-reporter -n dev

# View details and schedule
kubectl describe cronjob status-reporter -n dev

# Check last scheduled time
kubectl get cronjob status-reporter -n dev -o jsonpath='{.status.lastScheduleTime}'
```

### View Job History

```bash
# View recent jobs
kubectl get jobs -n dev | grep status-reporter

# View pods from jobs
kubectl get pods -n dev -l app=status-reporter --sort-by=.metadata.creationTimestamp

# View logs from specific job
kubectl logs -n dev job/status-reporter-<timestamp>
```

### RabbitMQ Monitoring

```bash
# Check queue status
kubectl exec -n dev rabitmq-cluster-server-0 -- \
  rabbitmqctl list_queues name messages messages_ready messages_unacknowledged

# Peek at queue (if rabbitmqadmin available)
kubectl exec -n dev rabitmq-cluster-server-0 -- \
  rabbitmqadmin get queue=slack_send_message_queue count=1
```

## Troubleshooting

### Pod Won't Start

```bash
# Check pod status
kubectl describe pod -n dev -l app=status-reporter

# Common issues:
# - ImagePullBackOff: Image not in registry or permissions issue
# - CrashLoopBackOff: Check logs for Python errors
```

### Permission Issues

```bash
# Verify ServiceAccount has permissions
kubectl auth can-i get pods --as=system:serviceaccount:dev:status-reporter -n dev
kubectl auth can-i list pods --as=system:serviceaccount:dev:status-reporter -n dev

# Check RBAC
kubectl get role status-reporter-role -n dev -o yaml
kubectl get rolebinding status-reporter-binding -n dev -o yaml
```

### RabbitMQ Connection Issues

```bash
# Check RabbitMQ secret exists
kubectl get secret rabbitmq-gds-qa -n dev

# Check ConfigMap
kubectl get configmap status-reporter-config -n dev -o yaml

# Check RabbitMQ service
kubectl get svc rabitmq-cluster -n dev
```

### Test Locally

```bash
# Test script locally (requires kubectl configured)
cd ~/status-reporter
export RABBITMQ_HOST="35.199.22.143"  # External IP for testing
export RABBITMQ_PORT="5672"
export RABBITMQ_QUEUE="slack_send_message_queue"
export RABBITMQ_USER="GDS_service_QA"
export RABBITMQ_PASS="<password>"

python3 status_reporter.py
```

## Files

- **`status_reporter.py`** - Main Python script
- **`Dockerfile`** - Container image definition  
- **`cronjob-artifactregistry.yaml`** - Production Kubernetes manifest (Artifact Registry)
- **`cronjob.yaml`** - Legacy manifest (GCR - not used)
- **`Jenkinsfile.artifactregistry`** - Production Jenkins pipeline
- **`Jenkinsfile`** - Legacy Jenkins pipeline (not used)
- **`Jenkinsfile.parameterized`** - Advanced Jenkins pipeline (not used)
- **`deploy.sh`** - Quick deployment script
- **`README.md`** - This file
- **`JENKINS.md`** - Jenkins setup guide
- **`DEPLOYMENT_STATUS.md`** - Deployment documentation
- **`ARTIFACT_REGISTRY_MIGRATION.md`** - Migration from GCR guide
- **`MARKDOWN_FORMAT.md`** - Message format documentation
- **`GITHUB_MIGRATION.md`** - GitHub repository setup

## Development

### Making Changes

```bash
# 1. Make changes locally
cd /Users/michael/workspace/status-reporter
# Edit files...

# 2. Commit and push
git add .
git commit -m "Description of changes"
git push origin main

# 3. Deploy on jenkins-t375
ssh jenkins-t375
cd ~/status-reporter
git pull origin main
docker build -t us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/status-reporter:qa-latest .
docker push us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/status-reporter:qa-latest
kubectl apply -f cronjob-artifactregistry.yaml

# 4. Test
kubectl create job --from=cronjob/status-reporter test-update -n dev
kubectl logs -n dev -l app=status-reporter --tail=100
```

### Testing Changes

Always test after making changes:

```bash
# Run manual test job
kubectl create job --from=cronjob/status-reporter test-$(date +%s) -n dev

# Monitor
kubectl get pods -n dev -l app=status-reporter -w

# Check logs
kubectl logs -n dev -l app=status-reporter --tail=100

# Verify RabbitMQ
kubectl exec -n dev rabitmq-cluster-server-0 -- \
  rabbitmqctl list_queues name messages | grep slack_send_message_queue
```

## Health Score Calculation

```python
health_score = (healthy_pods / total_pods) * 100

Emoji indicators:
- 🟢 >= 95% - Excellent health
- 🟡 80-94% - Good health with some issues  
- 🔴 < 80% - Poor health, needs attention
```

## Support

- **GitHub Issues:** https://github.com/cropx/status-reporter/issues
- **Documentation:** See files in repository root
- **Slack Channel:** Messages posted to `C0ADXA2FXH9`

## License

Internal CropX tool - All rights reserved.
