#!/usr/bin/env python3
"""Create JSON files for questions 3-30 with looked-up answers."""

import json
import re
from pathlib import Path

QUESTIONS_DIR = Path(__file__).parent.parent
JSON_DIR = QUESTIONS_DIR / "json_questions"

# Answers looked up from Perplexity/ExamTopics
ANSWERS = {
    3: "A",   # aws:PrincipalOrgID condition key
    4: "A",   # Gateway VPC endpoint
    5: "C",   # Copy to EFS
    6: "B",   # Snowball Edge
    7: "D",   # SNS with multiple SQS subscriptions
    8: "B",   # SQS + Auto Scaling based on queue size
    9: "B",   # S3 File Gateway with lifecycle
    10: "B",  # SQS FIFO + Lambda
    11: "A",  # Secrets Manager with rotation
    12: "A",  # CloudFront with S3 and ALB origins
    13: "A",  # Secrets Manager multi-region with rotation
    14: "C",  # Aurora Multi-AZ with Auto Scaling
    15: "C",  # AWS Network Firewall
    16: "B",  # QuickSight with users and groups
    17: "A",  # IAM role attached to EC2
    18: "AB", # SQS queue + Lambda invocation (choose two)
    19: "D",  # Gateway Load Balancer
    20: "D",  # EBS fast snapshot restore
    21: "B",  # S3 + CloudFront + DynamoDB
    22: "B",  # S3 Standard
    23: "C",  # Lifecycle to S3 Standard-IA
    24: "D",  # Service Catalog with approved types
    25: "C",  # Aurora Serverless
    26: "B",  # AWS Config managed rule
    27: "C",  # GetMetricWidgetImage API
    28: "A",  # Transit Gateway with RAM
    29: "C",  # Global Accelerator
    30: "C",  # Snapshot + delete + restore
}

def parse_questions():
    """Parse questions 3-30 from page files."""
    content = ""
    for page in ["page1.txt", "page2.txt", "page3.txt"]:
        filepath = QUESTIONS_DIR / page
        if filepath.exists():
            with open(filepath) as f:
                content += f.read()

    parts = re.split(r'Question #(\d+)', content)
    questions = {}

    for i in range(1, len(parts) - 1, 2):
        q_num = int(parts[i])
        if 3 <= q_num <= 30:
            questions[q_num] = parts[i + 1].strip()

    return questions

def parse_question_content(q_num, content):
    """Parse question content into structured format."""
    lines = content.split('\n')

    # Extract topic
    topic = 1
    topic_match = re.search(r'Topic\s*(\d+)', lines[0] if lines else '')
    if topic_match:
        topic = int(topic_match.group(1))
        lines = lines[1:]

    text = '\n'.join(lines).strip()

    # Find where options start
    option_match = re.search(r'\n([A-F])\.\s+', text)
    if not option_match:
        return None

    question_text = text[:option_match.start()].strip()
    options_text = text[option_match.start():]

    # Parse options
    options = {}
    option_matches = list(re.finditer(r'\n?([A-F])\.\s+', options_text))

    for idx, match in enumerate(option_matches):
        letter = match.group(1)
        start = match.end()

        if idx + 1 < len(option_matches):
            end = option_matches[idx + 1].start()
        else:
            end = len(options_text)

        option_text = options_text[start:end].strip()
        # Clean up
        option_text = re.sub(r'\s*Most Voted\s*', '', option_text)
        option_text = re.sub(r'\s*\n\s*Correct Answer.*$', '', option_text, flags=re.DOTALL)
        options[letter] = option_text.strip()

    return {
        'question_number': q_num,
        'topic': topic,
        'question_text': question_text,
        'options': options,
        'correct_answer': ANSWERS.get(q_num),
        'community_vote': None
    }

def main():
    questions = parse_questions()
    print(f"Found {len(questions)} questions to process")

    created = 0
    for q_num, content in sorted(questions.items()):
        json_path = JSON_DIR / f"question_{q_num}.json"

        if json_path.exists():
            print(f"  Skipping Q{q_num} (already exists)")
            continue

        question = parse_question_content(q_num, content)
        if question and question['correct_answer']:
            with open(json_path, 'w') as f:
                json.dump(question, f, indent=2)
            print(f"  Created question_{q_num}.json (Answer: {question['correct_answer']})")
            created += 1
        else:
            print(f"  Failed to parse Q{q_num}")

    print(f"\nCreated {created} new JSON files")

if __name__ == "__main__":
    main()
