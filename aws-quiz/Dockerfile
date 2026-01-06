FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY aws-quiz/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY aws-quiz/app.py aws-quiz/models.py ./
COPY aws-quiz/import_questions.py aws-quiz/parse_text_questions.py ./
COPY aws-quiz/create_missing_questions.py ./
COPY aws-quiz/templates/ templates/
COPY aws-quiz/static/ static/

# Create data directory for SQLite database
RUN mkdir -p data

# Copy question source files
COPY json_questions/ /questions/json_questions/
COPY page*.txt /questions/

# Update import script paths for container
RUN sed -i 's|Path(__file__).parent.parent / "json_questions"|Path("/questions/json_questions")|g' import_questions.py && \
    sed -i 's|QUESTIONS_DIR = Path(__file__).parent.parent|QUESTIONS_DIR = Path("/questions")|g' parse_text_questions.py && \
    sed -i 's|QUESTIONS_DIR = Path(__file__).parent.parent|QUESTIONS_DIR = Path("/questions")|g' create_missing_questions.py

# Import questions at build time
RUN python parse_text_questions.py && python create_missing_questions.py && python import_questions.py

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5050

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "2", "app:app"]
