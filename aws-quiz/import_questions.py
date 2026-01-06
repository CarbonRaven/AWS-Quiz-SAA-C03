#!/usr/bin/env python3
"""Import questions from JSON files into SQLite database."""

import json
import re
from pathlib import Path
from models import get_db, init_db

# Path to JSON questions (relative to this script)
JSON_DIR = Path(__file__).parent.parent / "json_questions"

# AWS services to detect in questions for auto-tagging
AWS_SERVICES = [
    "S3", "EC2", "EBS", "EFS", "RDS", "DynamoDB", "Aurora",
    "Lambda", "API Gateway", "CloudFront", "Route 53", "Route53",
    "VPC", "IAM", "CloudWatch", "CloudTrail", "SNS", "SQS",
    "Kinesis", "Redshift", "Athena", "EMR", "Glue",
    "ElastiCache", "ECS", "EKS", "Fargate", "ECR",
    "CloudFormation", "Elastic Beanstalk", "CodePipeline", "CodeBuild", "CodeDeploy",
    "Secrets Manager", "Systems Manager", "Parameter Store",
    "KMS", "ACM", "WAF", "Shield", "GuardDuty", "Inspector",
    "Config", "Organizations", "Control Tower", "RAM",
    "Direct Connect", "Transit Gateway", "VPN", "PrivateLink",
    "Storage Gateway", "DataSync", "Transfer Family", "Snow",
    "Backup", "FSx", "Global Accelerator", "Auto Scaling",
    "ALB", "NLB", "ELB", "Elastic Load Balancer",
    "SageMaker", "Rekognition", "Comprehend", "Textract", "Polly", "Lex",
    "Step Functions", "EventBridge", "AppSync", "Amplify",
    "Cognito", "Directory Service", "SSO", "Identity Center",
    "Cost Explorer", "Budgets", "Trusted Advisor", "Well-Architected",
    "X-Ray", "Service Catalog", "License Manager",
    "Neptune", "DocumentDB", "QLDB", "Timestream", "Keyspaces",
    "MQ", "MSK", "OpenSearch", "Elasticsearch",
    "Outposts", "Wavelength", "Local Zones"
]

def extract_tags(text):
    """Extract AWS service tags from question text."""
    tags = set()
    text_upper = text.upper()

    for service in AWS_SERVICES:
        # Create pattern that matches the service name as a word
        pattern = r'\b' + re.escape(service.upper()) + r'\b'
        if re.search(pattern, text_upper):
            # Normalize the tag
            tag = service.replace(" ", "-")
            tags.add(tag)

    return sorted(list(tags))

def import_questions():
    """Import all questions from JSON files."""
    print("Initializing database...")
    init_db()

    conn = get_db()

    # Get existing question numbers to avoid duplicates
    existing = set(
        row[0] for row in
        conn.execute("SELECT question_number FROM questions").fetchall()
    )

    json_files = sorted(JSON_DIR.glob("question_*.json"))
    print(f"Found {len(json_files)} JSON files")

    imported = 0
    skipped = 0

    for json_file in json_files:
        with open(json_file, 'r') as f:
            data = json.load(f)

        q_num = data.get('question_number')
        if q_num in existing:
            skipped += 1
            continue

        # Extract tags from question text
        question_text = data.get('question_text', '')
        tags = extract_tags(question_text)

        # Also check options for service mentions
        options = data.get('options', {})
        for opt_text in options.values():
            tags.extend(extract_tags(opt_text))
        tags = sorted(list(set(tags)))

        # Serialize to JSON strings
        options_json = json.dumps(options)
        tags_json = json.dumps(tags)
        community_vote = data.get('community_vote')
        community_vote_json = json.dumps(community_vote) if community_vote else None

        # Build params tuple
        params = (
            q_num,
            data.get('topic'),
            question_text,
            options_json,
            data.get('correct_answer'),
            community_vote_json,
            tags_json
        )

        conn.execute(
            """INSERT INTO questions
               (question_number, topic, question_text, options, correct_answer, community_vote, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            params
        )
        imported += 1

    conn.commit()
    conn.close()

    print(f"Imported: {imported} questions")
    print(f"Skipped (already exist): {skipped} questions")

    # Print tag statistics
    conn = get_db()
    all_tags = conn.execute("SELECT tags FROM questions").fetchall()
    conn.close()

    tag_counts = {}
    for row in all_tags:
        for tag in json.loads(row[0]):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print("\nTop AWS services in questions:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {tag}: {count}")

if __name__ == "__main__":
    import_questions()
