from models import Question, Answer
from app import db

class QuizEngine:
    """Handle quiz logic and scoring"""
    
    def calculate_score(self, quiz_id, user_answers):
        """
        Calculate score for submitted quiz
        
        Args:
            quiz_id: ID of the quiz
            user_answers: Dictionary of {question_id: user_selected_answer}
        
        Returns:
            Tuple of (score, detailed_results)
        """
        score = 0
        details = []
        
        for question_id, selected_answer in user_answers.items():
            question = Question.query.get(question_id)
            if not question:
                continue
            
            is_correct = selected_answer.lower().strip() == question.correct_answer.lower().strip()
            
            if is_correct:
                score += 1
            
            details.append({
                'question_id': question_id,
                'question': question.text,
                'user_answer': selected_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation
            })
        
        return score, details
    
    def get_performance_stats(self, user_id=None):
        """
        Get performance statistics
        """
        from models import UserQuizAttempt
        
        if user_id:
            attempts = UserQuizAttempt.query.filter_by(user_id=user_id).all()
        else:
            attempts = UserQuizAttempt.query.all()
        
        if not attempts:
            return {
                'total_attempts': 0,
                'average_score': 0,
                'total_questions_answered': 0
            }
        
        total_score = sum([att.score for att in attempts])
        total_questions = sum([att.total_questions for att in attempts])
        
        return {
            'total_attempts': len(attempts),
            'average_score': total_score / len(attempts) if attempts else 0,
            'total_questions_answered': total_questions,
            'average_percentage': (total_score / total_questions * 100) if total_questions > 0 else 0
        }
