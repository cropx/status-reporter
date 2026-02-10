pipeline {
    agent any
    
    environment {
        PROJECT_ID = 'crx-dev-svc'
        IMAGE_NAME = 'status-reporter'
        IMAGE_TAG = 'latest'
        GCR_IMAGE = "gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"
        NAMESPACE = 'dev'
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    echo "Using files from ~/status-reporter"
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                dir('/home/michael/status-reporter') {
                    script {
                        echo "Building Docker image: ${GCR_IMAGE}"
                        sh """
                            docker build -t ${GCR_IMAGE} .
                        """
                    }
                }
            }
        }
        
        stage('Configure Docker for GCR') {
            steps {
                script {
                    echo "Configuring Docker authentication for GCR"
                    sh """
                        gcloud auth configure-docker gcr.io --quiet
                    """
                }
            }
        }
        
        stage('Push to GCR') {
            steps {
                script {
                    echo "Pushing image to GCR: ${GCR_IMAGE}"
                    sh """
                        docker push ${GCR_IMAGE}
                    """
                }
            }
        }
        
        stage('Deploy/Update CronJob') {
            steps {
                dir('/home/michael/status-reporter') {
                    script {
                        echo "Applying CronJob manifest to ${NAMESPACE} namespace"
                        sh """
                            kubectl apply -f cronjob.yaml
                        """
                    }
                }
            }
        }
        
        stage('Verify Deployment') {
            steps {
                script {
                    echo "Verifying CronJob deployment"
                    sh """
                        kubectl get cronjob status-reporter -n ${NAMESPACE}
                        kubectl describe cronjob status-reporter -n ${NAMESPACE} | grep -A 3 "Schedule"
                    """
                }
            }
        }
        
        stage('Test Manual Run (Optional)') {
            when {
                expression { params.RUN_TEST == true }
            }
            steps {
                script {
                    echo "Creating test job"
                    def timestamp = sh(script: 'date +%s', returnStdout: true).trim()
                    sh """
                        kubectl create job --from=cronjob/status-reporter test-run-${timestamp} -n ${NAMESPACE}
                        sleep 10
                        kubectl get jobs -n ${NAMESPACE} | grep test-run-${timestamp}
                        kubectl get pods -n ${NAMESPACE} -l app=status-reporter
                    """
                }
            }
        }
    }
    
    post {
        success {
            echo """
            ========================================
            ✓ QA Status Reporter Deployed Successfully!
            ========================================
            Image: ${GCR_IMAGE}
            Namespace: ${NAMESPACE}
            Schedule: Daily at 8:00 AM UTC
            
            To verify:
            - kubectl get cronjob status-reporter -n dev
            - kubectl logs -n dev -l app=status-reporter --tail=50
            ========================================
            """
        }
        failure {
            echo """
            ========================================
            ✗ Deployment Failed!
            ========================================
            Check the logs above for errors.
            ========================================
            """
        }
        always {
            script {
                echo "Cleaning up old Docker images"
                sh """
                    docker image prune -f || true
                """
            }
        }
    }
}
