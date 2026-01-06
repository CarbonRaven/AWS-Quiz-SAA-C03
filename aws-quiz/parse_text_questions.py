#!/usr/bin/env python3
"""Parse questions from page*.txt files and save as JSON."""

import json
import re
from pathlib import Path

# Paths
QUESTIONS_DIR = Path(__file__).parent.parent
JSON_DIR = QUESTIONS_DIR / "json_questions"

def parse_page_file(filepath):
    """Parse a page*.txt file and extract questions."""
    with open(filepath, 'r') as f:
        content = f.read()

    questions = []

    # Split by "Question #" pattern
    parts = re.split(r'Question #(\d+)', content)

    # parts[0] is empty/header, then alternating: number, content, number, content...
    i = 1
    while i < len(parts) - 1:
        q_num = int(parts[i])
        q_content = parts[i + 1].strip()
        i += 2

        # Parse the question content
        question = parse_question_content(q_num, q_content)
        if question:
            questions.append(question)

    return questions

def parse_question_content(q_num, content):
    """Parse individual question content."""
    lines = content.split('\n')

    # First line usually has "Topic X"
    topic = 1
    topic_match = re.search(r'Topic\s*(\d+)', lines[0] if lines else '')
    if topic_match:
        topic = int(topic_match.group(1))
        lines = lines[1:]  # Remove topic line

    # Join remaining content
    text = '\n'.join(lines).strip()

    # Split into question text and options
    # Options start with "A. " or "A:" pattern
    option_pattern = r'\n([A-F])\.\s+'

    # Find where options start
    option_match = re.search(option_pattern, text)
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

        # Find end of this option (start of next option or end of string)
        if idx + 1 < len(option_matches):
            end = option_matches[idx + 1].start()
        else:
            # Find where answer section starts
            end_markers = [
                r'\nCorrect Answer:',
                r'\n\s*Correct Answer',
                r'\n🗳️',
                r'\nCommunity vote',
            ]
            end = len(options_text)
            for marker in end_markers:
                marker_match = re.search(marker, options_text[start:])
                if marker_match:
                    end = min(end, start + marker_match.start())

        option_text = options_text[start:end].strip()
        # Clean up "Most Voted" tags
        option_text = re.sub(r'\s*Most Voted\s*$', '', option_text)
        options[letter] = option_text

    # Find correct answer
    correct_answer = None
    answer_match = re.search(r'Correct Answer:\s*([A-F]+)', text)
    if answer_match:
        correct_answer = answer_match.group(1)

    # Parse community vote distribution
    community_vote = None
    vote_match = re.search(r'Community vote distribution\s*\n(.+?)(?:\n\n|\Z)', text, re.DOTALL)
    if vote_match:
        vote_text = vote_match.group(1)
        # Parse patterns like "A (94%)" or "C (99%)"
        vote_pattern = r'([A-F]+)\s*\((\d+)%\)'
        votes = re.findall(vote_pattern, vote_text)
        if votes:
            community_vote = {letter: f"{pct}%" for letter, pct in votes}

    # If no correct answer found, try to infer from "Most Voted" marker
    if not correct_answer:
        for letter, opt_text in options.items():
            if 'Most Voted' in opt_text:
                correct_answer = letter
                # Clean up the option text
                options[letter] = re.sub(r'\s*Most Voted\s*', '', opt_text).strip()
                break

    # If still no correct answer, use highest community vote
    if not correct_answer and community_vote:
        # Get answer with highest vote percentage
        best_answer = max(community_vote.keys(), key=lambda k: int(community_vote[k].rstrip('%')))
        correct_answer = best_answer

    if not question_text or not options or not correct_answer:
        return None

    return {
        'question_number': q_num,
        'topic': topic,
        'question_text': question_text,
        'options': options,
        'correct_answer': correct_answer,
        'community_vote': community_vote
    }

def main():
    """Parse all page files and save as JSON."""
    page_files = sorted(QUESTIONS_DIR.glob("page*.txt"))
    print(f"Found {len(page_files)} page files")

    all_questions = []
    for page_file in page_files:
        questions = parse_page_file(page_file)
        all_questions.extend(questions)
        print(f"  {page_file.name}: {len(questions)} questions")

    print(f"\nTotal questions parsed: {len(all_questions)}")

    # Save as individual JSON files
    JSON_DIR.mkdir(exist_ok=True)
    saved = 0
    skipped = 0

    for q in all_questions:
        q_num = q['question_number']
        json_path = JSON_DIR / f"question_{q_num}.json"

        if json_path.exists():
            skipped += 1
            continue

        with open(json_path, 'w') as f:
            json.dump(q, f, indent=2)
        saved += 1

    print(f"Saved: {saved} new JSON files")
    print(f"Skipped: {skipped} (already exist)")

if __name__ == "__main__":
    main()
