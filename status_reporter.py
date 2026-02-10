#!/usr/bin/env python3
"""
QA Dev Namespace Status Reporter
Generates daily status report and sends to RabbitMQ
"""
import json
import os
import subprocess
import sys
from datetime import datetime
import pika

def get_pod_status():
    """Get all pods status from dev namespace"""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", "dev", "--no-headers"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error getting pods: {e}"

def parse_pods(pod_output):
    """Parse pod status and categorize"""
    lines = pod_output.strip().split('\n')
    
    critical = []
    warnings = []
    healthy = []
    
    for line in lines:
        if not line:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
            
        name = parts[0]
        ready = parts[1]
        status = parts[2]
        restarts = int(parts[3]) if parts[3].isdigit() else 0
        
        if 'CrashLoopBackOff' in status:
            critical.append({"name": name, "status": status, "restarts": restarts})
        elif restarts > 100:
            warnings.append({"name": name, "status": status, "restarts": restarts})
        elif status == "Running":
            healthy.append({"name": name, "status": status, "restarts": restarts})
    
    return critical, warnings, healthy

def generate_report():
    """Generate the status report"""
    pod_output = get_pod_status()
    critical, warnings, healthy = parse_pods(pod_output)
    
    total_pods = len(critical) + len(warnings) + len(healthy)
    health_score = int((len(healthy) / total_pods * 100)) if total_pods > 0 else 0
    
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "namespace": "dev",
        "environment": "QA",
        "summary": {
            "total_pods": total_pods,
            "healthy": len(healthy),
            "warnings": len(warnings),
            "critical": len(critical),
            "health_score": health_score
        },
        "critical_issues": critical[:10],  # Top 10
        "warnings": warnings[:10],  # Top 10
        "healthy_count": len(healthy)
    }
    
    return report

def format_markdown_message(report):
    """Format report as markdown text"""
    timestamp = report['timestamp']
    summary = report['summary']
    
    # Choose emoji based on health score
    if summary['health_score'] >= 95:
        health_emoji = "🟢"
    elif summary['health_score'] >= 80:
        health_emoji = "🟡"
    else:
        health_emoji = "🔴"
    
    markdown = f"""# {health_emoji} QA Environment Status Report

**Environment:** {report['environment']}  
**Namespace:** {report['namespace']}  
**Timestamp:** {timestamp}

## 📊 Summary

- **Health Score:** {summary['health_score']}%
- **Total Pods:** {summary['total_pods']}
- **Healthy:** {summary['healthy']} ✅
- **Warnings:** {summary['warnings']} ⚠️
- **Critical:** {summary['critical']} 🔴

"""
    
    # Add critical issues
    if report['critical_issues']:
        markdown += "## 🔴 Critical Issues\n\n"
        for issue in report['critical_issues']:
            markdown += f"- **{issue['name']}**\n"
            markdown += f"  - Status: `{issue['status']}`\n"
            markdown += f"  - Restarts: {issue['restarts']}\n\n"
    
    # Add warnings
    if report['warnings']:
        markdown += "## ⚠️ Warnings (High Restart Count)\n\n"
        for warn in report['warnings']:
            markdown += f"- **{warn['name']}**\n"
            markdown += f"  - Status: `{warn['status']}`\n"
            markdown += f"  - Restarts: {warn['restarts']}\n\n"
    
    # Add healthy summary
    markdown += f"## ✅ Healthy Services\n\n{summary['healthy']} pods running normally\n"
    
    return markdown

def send_to_rabbitmq(report):
    """Send report to RabbitMQ queue"""
    
    # Get credentials from environment or k8s secret
    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabitmq-cluster')
    rabbitmq_port = int(os.getenv('RABBITMQ_PORT', '5672'))
    rabbitmq_user = os.getenv('RABBITMQ_USER', 'GDS_service_QA')
    rabbitmq_pass = os.getenv('RABBITMQ_PASS', '@Hh13QT05&GU')
    
    queue_name = os.getenv('RABBITMQ_QUEUE', 'slack_send_message_queue')
    
    # Format as markdown
    markdown_text = format_markdown_message(report)
    
    # Create message in required format
    message = {
        "message": markdown_text,
        "source": "QA_LIVE"
    }
    
    try:
        # Connect to RabbitMQ
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
        parameters = pika.ConnectionParameters(
            host=rabbitmq_host,
            port=rabbitmq_port,
            credentials=credentials,
            connection_attempts=3,
            retry_delay=2
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declare queue (idempotent)
        channel.queue_declare(
            queue=queue_name,
            durable=True
        )
        
        # Publish message to queue
        channel.basic_publish(
            exchange='',  # Default exchange (direct to queue)
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                content_type='application/json'
            )
        )
        
        connection.close()
        print(f"✓ Report sent to RabbitMQ queue '{queue_name}'")
        print(f"  Health Score: {report['summary']['health_score']}%")
        print(f"  Critical: {report['summary']['critical']}, Warnings: {report['summary']['warnings']}, Healthy: {report['summary']['healthy']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error sending to RabbitMQ: {e}", file=sys.stderr)
        return False

def main():
    print(f"=== QA Status Reporter - {datetime.utcnow().isoformat()}Z ===")
    
    # Generate report
    report = generate_report()
    
    # Print summary
    print(f"\nReport Summary:")
    print(f"  Total Pods: {report['summary']['total_pods']}")
    print(f"  Health Score: {report['summary']['health_score']}%")
    print(f"  Critical Issues: {report['summary']['critical']}")
    print(f"  Warnings: {report['summary']['warnings']}")
    
    # Send to RabbitMQ
    success = send_to_rabbitmq(report)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
