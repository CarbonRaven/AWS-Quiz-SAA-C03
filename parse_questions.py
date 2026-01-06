#!/usr/bin/env python3
"""
Parse AWS exam questions from text files and create individual JSON files.
"""

import re
import json
import os

def parse_questions(content):
    """Parse questions from text content."""
    questions = []

    # Split content by question pattern
    question_pattern = r'Question #(\d+)Topic (\d+)\n'
    parts = re.split(question_pattern, content)

    # parts[0] is before first question, then [num, topic, content] repeats
    i = 1
    while i < len(parts) - 2:
        question_num = parts[i]
        topic = parts[i + 1]
        question_content = parts[i + 2]

        # Parse the question content
        question_data = parse_question_content(question_num, topic, question_content)
        if question_data:
            questions.append(question_data)

        i += 3

    return questions

def parse_question_content(question_num, topic, content):
    """Parse individual question content."""
    lines = content.strip().split('\n')

    # Find the question text (before options)
    question_text_lines = []
    options = {}
    correct_answer = None
    community_vote = None

    option_pattern = r'^([A-F])\.\s+(.+)$'
    correct_pattern = r'^Correct Answer:\s*([A-F]+)'
    vote_pattern = r'^([A-F]+)\s+\((\d+%)\)'

    current_option = None
    in_options = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for correct answer
        correct_match = re.match(correct_pattern, line)
        if correct_match:
            correct_answer = correct_match.group(1).strip()
            continue

        # Check for community vote distribution header
        if line == "Community vote distribution":
            continue

        # Check for vote distribution
        vote_match = re.match(vote_pattern, line)
        if vote_match:
            if community_vote is None:
                community_vote = {}
            community_vote[vote_match.group(1)] = vote_match.group(2)
            continue

        # Skip "Most Voted" suffix and emoji
        line_clean = re.sub(r'\s*Most Voted\s*$', '', line)
        line_clean = re.sub(r'\s*🗳️\s*$', '', line_clean)

        # Check for option
        option_match = re.match(option_pattern, line_clean)
        if option_match:
            in_options = True
            current_option = option_match.group(1)
            options[current_option] = option_match.group(2)
            continue

        # If we're in options and line doesn't match option pattern, it's continuation
        if in_options and current_option and line_clean and not line_clean.startswith('Correct'):
            # Check if it's a percentage like "2%" or "13%"
            if re.match(r'^\d+%$', line_clean):
                continue
            # Check if it's "Other"
            if line_clean == "Other":
                continue
            options[current_option] += " " + line_clean
        elif not in_options:
            question_text_lines.append(line_clean)

    question_text = ' '.join(question_text_lines)

    # Clean up question text
    question_text = re.sub(r'\s+', ' ', question_text).strip()

    return {
        "question_number": int(question_num),
        "topic": int(topic),
        "question_text": question_text,
        "options": options,
        "correct_answer": correct_answer,
        "community_vote": community_vote
    }

def main():
    # Directory containing the question files
    questions_dir = "/Users/tom/Documents/research/AWS/questions"
    output_dir = os.path.join(questions_dir, "json_questions")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    all_questions = []

    # Process each page file
    for page_num in range(15, 25):
        filename = f"page{page_num}.txt"
        filepath = os.path.join(questions_dir, filename)

        print(f"Processing {filename}...")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove line numbers from the content
        content = re.sub(r'^\s*\d+→', '', content, flags=re.MULTILINE)

        questions = parse_questions(content)
        all_questions.extend(questions)
        print(f"  Found {len(questions)} questions")

    print(f"\nTotal questions found: {len(all_questions)}")

    # Write individual JSON files for each question
    for q in all_questions:
        output_file = os.path.join(output_dir, f"question_{q['question_number']}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(q, f, indent=2, ensure_ascii=False)

    print(f"Created {len(all_questions)} JSON files in {output_dir}")

if __name__ == "__main__":
    main()
