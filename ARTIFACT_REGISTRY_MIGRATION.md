# Migration to Artifact Registry (Following gds_service Pattern)

## 🔍 Problem Identified

The original solution tried to use GCR (`gcr.io/crx-dev-svc`) but the service account didn't have permission.

**After reviewing gds_service**, I found they use **Artifact Registry** instead:
- **gds_service uses:** `us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/gds-service`
- **We should use:** `us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/status-reporter`

## ✅ Solution

Use the **same Artifact Registry** that gds_service uses, which the jenkins-t375 service account already has access to!

### Changes Made

1. **Created `Jenkinsfile.artifactregistry`**
   - Follows exact pattern from `gds_service-qa-pipeline.groovy`
   - Uses Artifact Registry: `us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker`
   - Tags images as `qa-latest` and `${gitHash}`
   - Includes Slack notifications to `#deployments-qa`

2. **Created `cronjob-artifactregistry.yaml`**
   - Updated image path to Artifact Registry
   - Everything else remains the same

## 📊 Comparison: GDS Service vs QA Status Reporter

| Component | GDS Service | QA Status Reporter |
|-----------|-------------|-------------------|
| **Registry** | `us-east4-docker.pkg.dev` | `us-east4-docker.pkg.dev` ✅ |
| **Project** | `crx-infra-svc` | `crx-infra-svc` ✅ |
| **Repo** | `crx-infra-docker` | `crx-infra-docker` ✅ |
| **Artifact** | `gds-service` | `status-reporter` |
| **Full Path** | `us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/gds-service` | `us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/status-reporter` |
| **Tags** | `qa-latest`, `${gitHash}` | `qa-latest`, `${gitHash}` ✅ |
| **K8s Cluster** | `dev-kubernetes` | `dev-kubernetes` ✅ |
| **Namespace** | `dev` | `dev` ✅ |
| **Slack Channel** | `#deployments-qa` | `#deployments-qa` ✅ |

## 🚀 Deployment Steps

### Option 1: Manual Deployment (Quickest)

```bash
# Connect to jenkins-t375
bash ~/connect.sh qak

cd ~/status-reporter

# Get latest files
# (copy Jenkinsfile.artifactregistry and cronjob-artifactregistry.yaml from local machine)

# Build and push
export REPOSITORY_URL="us-east4-docker.pkg.dev"
export PROJECT_NAME="crx-infra-svc"
export DOCKER_REPO="crx-infra-docker"
export ARTIFACT_ID="status-reporter"
export FULL_IMAGE_NAME="${REPOSITORY_URL}/${PROJECT_NAME}/${DOCKER_REPO}/${ARTIFACT_ID}"

docker build -t ${ARTIFACT_ID}:qa-latest -t ${FULL_IMAGE_NAME}:qa-latest .
docker push ${FULL_IMAGE_NAME}:qa-latest

# Deploy
kubectl apply -f cronjob-artifactregistry.yaml

# Test immediately
kubectl create job --from=cronjob/status-reporter test-$(date +%s) -n dev
kubectl get pods -n dev -l app=status-reporter -w
```

### Option 2: Jenkins Pipeline

1. Create Jenkins job for QA Status Reporter
2. Use `Jenkinsfile.artifactregistry` 
3. Configure same way as gds_service job
4. Run with parameters:
   - `BRANCHGIT`: main
   - `RUN_TEST`: true
   - `FORCE_REBUILD`: false

## 🎯 Why This Works

The service account `tf-automation@crx-infra-svc.iam.gserviceaccount.com` already has permission to:
- ✅ Push to `us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/*`
- ✅ Access dev-kubernetes cluster
- ✅ Deploy to dev namespace

**Proof:** gds_service successfully deploys using this exact registry!

## 📝 Files Overview

### New Files
- `Jenkinsfile.artifactregistry` - Jenkins pipeline using Artifact Registry
- `cronjob-artifactregistry.yaml` - K8s manifest using Artifact Registry
- `ARTIFACT_REGISTRY_MIGRATION.md` - This document

### Original Files (Keep for reference)
- `Jenkinsfile` - Original (uses GCR - won't work)
- `Jenkinsfile.parameterized` - Original (uses GCR - won't work)
- `cronjob.yaml` - Original (uses GCR - won't work)

## 🔍 Verification Commands

```bash
# Check if image exists in Artifact Registry
gcloud artifacts docker images list \
  us-east4-docker.pkg.dev/crx-infra-svc/crx-infra-docker/status-reporter

# Check CronJob status
kubectl get cronjob status-reporter -n dev
kubectl describe cronjob status-reporter -n dev

# Check for running pods
kubectl get pods -n dev -l app=status-reporter

# View logs
kubectl logs -n dev -l app=status-reporter --tail=100

# Check RabbitMQ queue
kubectl exec -n dev rabitmq-cluster-server-0 -- \
  rabbitmqctl list_queues name messages | grep slack_send_message_queue
```

## 🎉 Expected Outcome

After deployment:
1. ✅ Docker image pushed successfully to Artifact Registry
2. ✅ CronJob updated with new image path
3. ✅ Test job runs and completes
4. ✅ Message appears in RabbitMQ `slack_send_message_queue`
5. ✅ Scheduled to run daily at 8:00 AM UTC
6. ✅ Slack notification sent to #deployments-qa

## 🔗 References

- gds_service pipeline: `/Users/michael/workspace/gds_service/infra/jenkins/gds_service-qa-pipeline.groovy`
- GDS Dockerfile: `/Users/michael/workspace/gds_service/Dockerfile`
- GDS K8s manifests: `/Users/michael/workspace/gds_service/infra/k8s/`
