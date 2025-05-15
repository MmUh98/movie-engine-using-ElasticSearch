from collections import deque
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class ContextEngine:
    def __init__(self, max_history=5):
        self.max_history = max_history
        self.query_history = deque(maxlen=max_history)
        self.movie_history = deque(maxlen=max_history)
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')

    def add_query(self, query, movie=None):
        """Add a new query and optionally the selected movie to the history"""
        self.query_history.append(query.lower())
        if movie:
            self.movie_history.append(movie)

    def get_context_terms(self):
        """Extract important terms from query history"""
        if not self.query_history:
            return []
        combined_queries = ' '.join(self.query_history)
        tfidf_matrix = self.vectorizer.fit_transform([combined_queries])
        feature_names = self.vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        top_indices = np.argsort(scores)[-5:]
        context_terms = [feature_names[i] for i in top_indices if scores[i] > 0]
        return context_terms

    def get_context_entities(self):
        """Extract genres, cast, and director from movie history for boosting"""
        genres = set()
        cast = set()
        directors = set()
        for movie in self.movie_history:
            genres.update(movie.get('genres', []))
            cast.update(movie.get('cast', []))
            if movie.get('director'):
                directors.add(movie['director'])
        return {
            'genres': list(genres),
            'cast': list(cast),
            'directors': list(directors)
        }

    def enhance_query(self, current_query):
        """Enhance the current query with context"""
        context_terms = self.get_context_terms()
        
        if not context_terms:
            return current_query
            
        # Combine current query with context terms
        enhanced_query = f"{current_query} {' '.join(context_terms)}"
        return enhanced_query

    def build_elasticsearch_query(self, query, context_terms, context_entities):
        """Build an Elasticsearch query that incorporates context"""
        should_clauses = []
        
        # Add main query
        should_clauses.append({
            "match": {
                "title": {
                    "query": query,
                    "boost": 3.0
                }
            }
        })
        
        should_clauses.append({
            "match": {
                "overview": {
                    "query": query,
                    "boost": 2.0
                }
            }
        })
        
        # Add context terms
        for term in context_terms:
            should_clauses.append({
                "match": {
                    "overview": {
                        "query": term,
                        "boost": 1.0
                    }
                }
            })
            
        # Add context entities (genres, cast, directors)
        for genre in context_entities.get('genres', []):
            should_clauses.append({
                "term": {
                    "genres": {
                        "value": genre,
                        "boost": 2.0
                    }
                }
            })
        for actor in context_entities.get('cast', []):
            should_clauses.append({
                "term": {
                    "cast": {
                        "value": actor,
                        "boost": 1.5
                    }
                }
            })
        for director in context_entities.get('directors', []):
            should_clauses.append({
                "term": {
                    "director": {
                        "value": director,
                        "boost": 2.0
                    }
                }
            })
            
        # Function score for custom re-ranking
        return {
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": should_clauses,
                            "minimum_should_match": 1
                        }
                    },
                    "boost_mode": "sum",
                    "score_mode": "sum"
                }
            }
        }

    def clear_history(self):
        """Clear the query history"""
        self.query_history.clear()
        self.movie_history.clear() 