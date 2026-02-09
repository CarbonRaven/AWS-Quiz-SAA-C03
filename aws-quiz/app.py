#!/usr/bin/env python3
"""Flask application for AWS Quiz."""

import json
import os
import secrets
from flask import Flask, render_template, jsonify, request, session
from models import (
    init_db, get_questions_for_session, get_question,
    record_answer, get_dashboard_stats, get_filter_counts, get_all_tags,
    get_question_explanation
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

@app.before_request
def ensure_db():
    """Ensure database is initialized."""
    init_db()

# --- Page Routes ---

@app.route('/')
def index():
    """Quiz home page."""
    counts = get_filter_counts()
    return render_template('index.html', counts=counts)

@app.route('/dashboard')
def dashboard():
    """Statistics dashboard."""
    stats = get_dashboard_stats()
    return render_template('dashboard.html', stats=stats)

# --- API Routes ---

@app.route('/api/start-session', methods=['POST'])
def start_session():
    """Start a new quiz session."""
    data = request.get_json()
    count = data.get('count', 10)
    filter_mode = data.get('filter', 'all')
    tags = data.get('tags')  # Optional list of AWS service tags

    questions = get_questions_for_session(count, filter_mode, tags)

    if not questions:
        return jsonify({'error': 'No questions available for this filter'}), 400

    # Store question IDs in session
    session['questions'] = [q['id'] for q in questions]
    session['current_index'] = 0
    session['score'] = 0
    session['answers'] = []
    session['tags'] = tags

    return jsonify({
        'total': len(questions),
        'filter': filter_mode,
        'tags': tags
    })

@app.route('/api/question')
def get_current_question():
    """Get the current question in the session."""
    if 'questions' not in session:
        return jsonify({'error': 'No active session'}), 400

    questions = session['questions']
    current_index = session.get('current_index', 0)

    if current_index >= len(questions):
        return jsonify({'complete': True, 'score': session.get('score', 0)})

    question = get_question(questions[current_index])
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    # Parse JSON fields
    question['options'] = json.loads(question['options'])
    question['tags'] = json.loads(question['tags'])

    # Don't send correct answer to client
    return jsonify({
        'index': current_index + 1,
        'total': len(questions),
        'question_number': question['question_number'],
        'question_text': question['question_text'],
        'options': question['options'],
        'tags': question['tags']
    })

@app.route('/api/answer', methods=['POST'])
def submit_answer():
    """Submit an answer for the current question."""
    if 'questions' not in session:
        return jsonify({'error': 'No active session'}), 400

    data = request.get_json()
    answer = data.get('answer')

    if not answer:
        return jsonify({'error': 'No answer provided'}), 400

    questions = session['questions']
    current_index = session.get('current_index', 0)

    if current_index >= len(questions):
        return jsonify({'error': 'Session complete'}), 400

    question = get_question(questions[current_index])
    correct_answer = question['correct_answer']
    is_correct = answer == correct_answer

    # Record the answer
    record_answer(question['id'], answer, is_correct)

    # Update session
    if is_correct:
        session['score'] = session.get('score', 0) + 1

    session['answers'] = session.get('answers', []) + [{
        'question_number': question['question_number'],
        'given': answer,
        'correct': correct_answer,
        'is_correct': is_correct
    }]

    # Move to next question
    session['current_index'] = current_index + 1
    session.modified = True

    # Get explanation for the question
    explanation = get_question_explanation(question['id'])

    return jsonify({
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'explanation': explanation,
        'score': session['score'],
        'has_next': session['current_index'] < len(questions)
    })

@app.route('/api/session-results')
def session_results():
    """Get results for the completed session."""
    if 'questions' not in session:
        return jsonify({'error': 'No active session'}), 400

    return jsonify({
        'total': len(session['questions']),
        'score': session.get('score', 0),
        'answers': session.get('answers', [])
    })

@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics."""
    return jsonify(get_dashboard_stats())

@app.route('/api/filter-counts')
def get_counts():
    """Get question counts for each filter, optionally filtered by tags."""
    tags = request.args.getlist('tags')
    return jsonify(get_filter_counts(tags if tags else None))

@app.route('/api/tags')
def get_tags():
    """Get all available AWS service tags with counts."""
    return jsonify(get_all_tags())

if __name__ == '__main__':
    print("Starting AWS Quiz on http://localhost:5050")
    app.run(debug=True, port=5050)
