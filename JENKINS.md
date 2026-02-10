# QA Status Reporter - Jenkins Pipeline

This directory contains Jenkins pipeline configurations for building and deploying the QA Status Reporter.

## Available Pipelines

### 1. Jenkinsfile (Simple)
Basic pipeline for straightforward deployments.

**Usage:**
```groovy
// In Jenkins, create a Pipeline job pointing to this Jenkinsfile
pipeline {
    definition {
        cps from SCM or Pipeline script from SCM
    }
}
```

### 2. Jenkinsfile.parameterized (Advanced)
Full-featured pipeline with parameters and testing options.

**Parameters:**
- `RUN_TEST`: Create a manual test job after deployment (default: false)
- `FORCE_REBUILD`: Force rebuild even if no changes detected (default: false)

**Features:**
- Build numbering (images tagged with build number + latest)
- Local image testing before push
- Optional manual test run
- RabbitMQ queue verification
- Automatic cleanup of old images

## Setup Instructions

### Option 1: Create Jenkins Job via UI

1. **Log into Jenkins** (on jenkins-t375 or Jenkins web interface)

2. **Create New Pipeline Job:**
   - Click "New Item"
   - Enter name: `status-reporter-deploy`
   - Select "Pipeline"
   - Click OK

3. **Configure Pipeline:**
   - Under "Pipeline" section:
     - Definition: `Pipeline script from SCM` OR `Pipeline script`
     - If using SCM: Point to your Git repo
     - If using script: Copy contents of `Jenkinsfile` or `Jenkinsfile.parameterized`
     - Script Path: `Jenkinsfile` (or `Jenkinsfile.parameterized`)

4. **Save and Build**

### Option 2: Create Job via Jenkins CLI

```bash
# Copy files to Jenkins server
scp Jenkinsfile* jenkins-t375:/home/michael/status-reporter/

# Create job using Jenkins CLI (if available)
# Or use the UI method above
```

### Option 3: Manual Run on Jenkins Machine

If you don't have Jenkins access, you can run the equivalent commands:

```bash
# SSH to jenkins-t375
ssh jenkins-t375

# Navigate to directory
cd ~/status-reporter

# Run the build and deploy steps manually
docker build -t gcr.io/crx-dev-svc/status-reporter:latest .
gcloud auth configure-docker gcr.io --quiet
docker push gcr.io/crx-dev-svc/status-reporter:latest
kubectl apply -f cronjob.yaml

# Verify
kubectl get cronjob status-reporter -n dev

# Optional: Test
kubectl create job --from=cronjob/status-reporter test-run-$(date +%s) -n dev
kubectl get pods -n dev -l app=status-reporter -w
```

## Pipeline Stages

### Simple Pipeline (Jenkinsfile)
1. **Checkout** - Verify files exist
2. **Build Docker Image** - Build the container
3. **Configure Docker for GCR** - Set up authentication
4. **Push to GCR** - Upload image to registry
5. **Deploy/Update CronJob** - Apply Kubernetes manifest
6. **Verify Deployment** - Confirm deployment success
7. **Test Manual Run** (optional) - Create test job

### Parameterized Pipeline (Jenkinsfile.parameterized)
1. **Validate Files** - Check all required files exist
2. **Build Docker Image** - Build with build number tag
3. **Test Image Locally** - Verify dependencies installed
4. **Configure Docker for GCR** - Set up authentication
5. **Push to GCR** - Upload both build number and latest tags
6. **Update CronJob** - Apply manifest
7. **Verify Deployment** - Show status and configuration
8. **Manual Test Run** (if enabled) - Create and monitor test job

## Monitoring After Deployment

### Check CronJob Status
```bash
kubectl get cronjob status-reporter -n dev
kubectl describe cronjob status-reporter -n dev
```

### View Logs
```bash
# Latest run
kubectl logs -n dev -l app=status-reporter --tail=100

# Specific job
kubectl get jobs -n dev | grep qa-status
kubectl logs -n dev job/status-reporter-<timestamp>
```

### Check RabbitMQ Queue
```bash
kubectl exec -n dev rabitmq-cluster-server-0 -- \
  rabbitmqctl list_queues name messages | grep slack_send_message_queue
```

### Manual Test
```bash
# Create test job
kubectl create job --from=cronjob/status-reporter manual-test -n dev

# Watch pod
kubectl get pods -n dev -l app=status-reporter -w

# View logs
kubectl logs -n dev -l app=status-reporter --tail=50
```

## Troubleshooting

### Build Fails
- Check Docker daemon is running: `systemctl status docker`
- Verify files exist: `ls -la ~/status-reporter/`
- Check Dockerfile syntax

### GCR Push Fails
- Verify GCR authentication: `gcloud auth configure-docker gcr.io --quiet`
- Check project permissions: `gcloud projects get-iam-policy crx-dev-svc`

### CronJob Not Running
- Check image pull: `kubectl describe pod <pod-name> -n dev`
- Verify schedule: `kubectl describe cronjob status-reporter -n dev`
- Check secrets exist: `kubectl get secret rabbitmq-gds-qa -n dev`

### RabbitMQ Connection Fails
- Verify credentials: `kubectl get secret rabbitmq-gds-qa -n dev -o yaml`
- Check service: `kubectl get svc rabitmq-cluster -n dev`
- Test from inside cluster: Create a debug pod

## Environment Variables

The CronJob uses these environment variables (from ConfigMap and Secrets):

- `RABBITMQ_HOST`: rabitmq-cluster
- `RABBITMQ_PORT`: 5672
- `RABBITMQ_QUEUE`: slack_send_message_queue
- `RABBITMQ_USER`: GDS_service_QA (from configmap)
- `RABBITMQ_PASS`: (from secret rabbitmq-gds-qa)

## Scheduled Execution

The CronJob runs automatically:
- **Schedule:** Daily at 8:00 AM UTC
- **Cron Expression:** `0 8 * * *`
- **Timezone:** UTC (no timezone specified = UTC)

To modify the schedule, edit `cronjob.yaml` and run the pipeline again.

## Files in This Directory

- `Jenkinsfile` - Simple pipeline
- `Jenkinsfile.parameterized` - Advanced pipeline with parameters
- `status_reporter.py` - Python script that generates and sends reports
- `Dockerfile` - Container image definition
- `cronjob.yaml` - Kubernetes CronJob manifest
- `deploy.sh` - Manual deployment script (alternative to Jenkins)
- `README.md` - General documentation
- `JENKINS.md` - This file

## Next Steps

1. Create Jenkins job using one of the Jenkinsfiles
2. Run the pipeline
3. Monitor first execution at 8:00 AM UTC tomorrow
4. Check RabbitMQ queue for messages
5. Verify Slack notifications (if configured)
