from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mcq_generator.db'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)
CORS(app)

from models import User, Quiz, Question, Answer, UserQuizAttempt
from mcq_generator import MCQGenerator
from quiz_engine import QuizEngine

# Initialize generators
mcq_gen = MCQGenerator()
quiz_engine = QuizEngine()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate')
def generate_page():
    return render_template('generate.html')

@app.route('/quiz/<int:quiz_id>')
def quiz_page(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return render_template('404.html'), 404
    return render_template('quiz.html', quiz_id=quiz_id)

@app.route('/results/<int:attempt_id>')
def results_page(attempt_id):
    attempt = UserQuizAttempt.query.get(attempt_id)
    if not attempt:
        return render_template('404.html'), 404
    return render_template('results.html', attempt_id=attempt_id)

# API Endpoints
@app.route('/api/generate', methods=['POST'])
def api_generate_mcq():
    """Generate MCQs from text input"""
    data = request.json
    text = data.get('text', '')
    num_questions = data.get('num_questions', 5)
    
    if not text or len(text) < 50:
        return jsonify({'error': 'Please provide text with at least 50 characters'}), 400
    
    try:
        questions = mcq_gen.generate(text, num_questions)
        
        # Save quiz to database
        quiz = Quiz(
            title=data.get('title', 'Generated Quiz'),
            description=data.get('description', ''),
            created_at=datetime.now()
        )
        db.session.add(quiz)
        db.session.flush()
        
        # Save questions
        for q_data in questions:
            question = Question(
                quiz_id=quiz.id,
                text=q_data['question'],
                correct_answer=q_data['correct_answer'],
                explanation=q_data.get('explanation', '')
            )
            db.session.add(question)
            db.session.flush()
            
            # Save options
            for option in q_data['options']:
                answer = Answer(
                    question_id=question.id,
                    text=option
                )
                db.session.add(answer)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'quiz_id': quiz.id,
            'num_questions': len(questions),
            'message': 'Quiz generated successfully!'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/quiz/<int:quiz_id>', methods=['GET'])
def api_get_quiz(quiz_id):
    """Get quiz details with questions"""
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    questions_data = []
    
    for q in questions:
        options = Answer.query.filter_by(question_id=q.id).all()
        questions_data.append({
            'id': q.id,
            'text': q.text,
            'options': [opt.text for opt in options],
            'explanation': q.explanation
        })
    
    return jsonify({
        'id': quiz.id,
        'title': quiz.title,
        'description': quiz.description,
        'num_questions': len(questions_data),
        'questions': questions_data,
        'created_at': quiz.created_at.isoformat()
    }), 200

@app.route('/api/submit', methods=['POST'])
def api_submit_quiz():
    """Submit quiz answers and get results"""
    data = request.json
    quiz_id = data.get('quiz_id')
    answers = data.get('answers')  # {question_id: selected_answer}
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    try:
        # Create attempt record
        attempt = UserQuizAttempt(
            quiz_id=quiz_id,
            submitted_at=datetime.now()
        )
        db.session.add(attempt)
        db.session.flush()
        
        # Calculate score
        score, details = quiz_engine.calculate_score(quiz_id, answers)
        attempt.score = score
        attempt.total_questions = len(answers)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'attempt_id': attempt.id,
            'score': score,
            'total': attempt.total_questions,
            'percentage': (score / attempt.total_questions * 100) if attempt.total_questions > 0 else 0,
            'details': details
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/results/<int:attempt_id>', methods=['GET'])
def api_get_results(attempt_id):
    """Get quiz attempt results"""
    attempt = UserQuizAttempt.query.get(attempt_id)
    if not attempt:
        return jsonify({'error': 'Attempt not found'}), 404
    
    quiz = Quiz.query.get(attempt.quiz_id)
    questions = Question.query.filter_by(quiz_id=attempt.quiz_id).all()
    
    results_detail = []
    for q in questions:
        options = Answer.query.filter_by(question_id=q.id).all()
        results_detail.append({
            'question': q.text,
            'correct_answer': q.correct_answer,
            'explanation': q.explanation,
            'options': [opt.text for opt in options]
        })
    
    return jsonify({
        'attempt_id': attempt.id,
        'quiz_title': quiz.title,
        'score': attempt.score,
        'total': attempt.total_questions,
        'percentage': (attempt.score / attempt.total_questions * 100) if attempt.total_questions > 0 else 0,
        'submitted_at': attempt.submitted_at.isoformat(),
        'results': results_detail
    }), 200

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    """Get user dashboard stats"""
    attempts = UserQuizAttempt.query.all()
    total_quizzes = len(attempts)
    avg_score = 0
    if attempts:
        avg_score = sum([att.score for att in attempts]) / total_quizzes
    
    return jsonify({
        'total_attempts': total_quizzes,
        'average_score': avg_score,
        'recent_attempts': [{
            'attempt_id': att.id,
            'quiz_id': att.quiz_id,
            'score': att.score,
            'total': att.total_questions,
            'submitted_at': att.submitted_at.isoformat()
        } for att in attempts[-5:]]
    }), 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
