import re
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class MCQGenerator:
    """Generate MCQs from text using NLP techniques"""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
    
    def generate(self, text, num_questions=5):
        """
        Generate MCQs from given text
        
        Args:
            text: Input text to generate questions from
            num_questions: Number of questions to generate
        
        Returns:
            List of MCQ dictionaries with question, options, and correct answer
        """
        sentences = sent_tokenize(text)
        
        if len(sentences) < num_questions:
            num_questions = max(1, len(sentences) - 1)
        
        questions = []
        
        for i in range(num_questions):
            if i < len(sentences):
                sentence = sentences[i]
                mcq = self._create_mcq_from_sentence(sentence, text)
                if mcq:
                    questions.append(mcq)
        
        return questions[:num_questions]
    
    def _create_mcq_from_sentence(self, sentence, full_text):
        """
        Create a single MCQ from a sentence
        """
        # Remove punctuation and create a blank
        words = word_tokenize(sentence)
        important_words = [w for w in words if w.lower() not in self.stop_words and len(w) > 3]
        
        if not important_words:
            return None
        
        # Select a random word to blank out
        blank_word = important_words[0]
        question_text = sentence.replace(blank_word, "______")
        
        # Generate wrong options
        all_words = word_tokenize(full_text)
        candidate_words = [w.lower() for w in all_words if w.lower() not in self.stop_words and len(w) > 3]
        candidate_words = list(set(candidate_words))
        
        wrong_options = []
        for word in candidate_words:
            if word.lower() != blank_word.lower() and len(wrong_options) < 3:
                wrong_options.append(word.capitalize())
        
        # Create options list
        options = [blank_word.capitalize()] + wrong_options
        if len(options) < 4:
            options += [f"Option {len(options)+1}"]
        
        return {
            'question': question_text,
            'options': options[:4],
            'correct_answer': blank_word.capitalize(),
            'explanation': f"The correct answer is '{blank_word}' because it completes the sentence meaningfully."
        }
