import os
import requests
import pandas as pd
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
import time

load_dotenv()

def robust_request(url, params, max_retries=5, sleep_time=0.5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response
            else:
                print(f"Error: {response.status_code}, retrying...")
        except Exception as e:
            print(f"Exception: {e}, retrying...")
        time.sleep(sleep_time)
    print("Max retries reached, skipping.")
    return None

class MovieDataLoader:
    def __init__(self):
        self.api_key = os.getenv('TMDB_API_KEY')
        if not self.api_key:
            raise ValueError("TMDB_API_KEY not found in environment variables")
            
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/w500"
        self.es = Elasticsearch(
            hosts=['http://127.0.0.1:9200'],
            basic_auth=('elastic', 'dEteLgD8*4BwAFXo3CmH'),
            verify_certs=False
        )

    def fetch_popular_movies(self, num_pages=50):
        """Fetch popular movies from TMDb API"""
        movies = []
        
        for page in range(1, num_pages + 1):
            url = f"{self.base_url}/movie/popular"
            params = {
                'api_key': self.api_key,
                'page': page,
                'language': 'en-US'
            }
            
            print(f"Fetching page {page}...")
            response = robust_request(url, params)
            if response:
                data = response.json()
                movies.extend(data['results'])
                print(f"Found {len(data['results'])} movies on page {page}")
            else:
                print(f"Error fetching page {page}: No response")
            time.sleep(0.4)  # Rate limiting
            
        return movies

    def get_movie_details(self, movie_id):
        """Get detailed information for a specific movie"""
        url = f"{self.base_url}/movie/{movie_id}"
        params = {
            'api_key': self.api_key,
            'language': 'en-US',
            'append_to_response': 'credits'
        }
        
        response = robust_request(url, params)
        if response:
            return response.json()
        else:
            print(f"Error fetching details for movie {movie_id}: No response")
        return None

    def process_movie_data(self, movies):
        """Process and format movie data for Elasticsearch"""
        processed_movies = []
        
        print(f"Processing {len(movies)} movies...")
        for i, movie in enumerate(movies, 1):
            print(f"Processing movie {i}/{len(movies)}: {movie['title']}")
            details = self.get_movie_details(movie['id'])
            if not details:
                print(f"Skipping movie {movie['title']} due to missing details")
                continue
                
            processed_movie = {
                'id': movie['id'],
                'title': movie['title'],
                'overview': movie['overview'],
                'poster_path': f"{self.image_base_url}{movie['poster_path']}" if movie['poster_path'] else None,
                'backdrop_path': f"{self.image_base_url}{movie['backdrop_path']}" if movie['backdrop_path'] else None,
                'release_date': movie['release_date'] if movie['release_date'] else None,
                'vote_average': movie['vote_average'],
                'genres': [genre['name'] for genre in details.get('genres', [])],
                'cast': [cast['name'] for cast in details.get('credits', {}).get('cast', [])[:5]],
                'director': next((crew['name'] for crew in details.get('credits', {}).get('crew', [])
                                if crew['job'] == 'Director'), None)
            }
            processed_movies.append(processed_movie)
            time.sleep(0.4)  # Rate limiting
            
        return processed_movies

    def create_index(self):
        """Create Elasticsearch index with proper mappings"""
        index_name = "movies"
        
        if self.es.indices.exists(index=index_name):
            print(f"Deleting existing index: {index_name}")
            self.es.indices.delete(index=index_name)
            
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "title": {
                        "type": "text",
                        "analyzer": "english"
                    },
                    "title_suggest": {
                        "type": "completion"
                    },
                    "overview": {"type": "text", "analyzer": "english"},
                    "poster_path": {"type": "keyword"},
                    "backdrop_path": {"type": "keyword"},
                    "release_date": {"type": "date"},
                    "vote_average": {"type": "float"},
                    "genres": {"type": "keyword"},
                    "cast": {"type": "keyword"},
                    "director": {"type": "keyword"}
                }
            }
        }
        
        print(f"Creating index: {index_name}")
        self.es.indices.create(index=index_name, body=mapping)
        return index_name

    def index_movies(self, movies):
        """Index movies in Elasticsearch"""
        index_name = self.create_index()
        
        print(f"Indexing {len(movies)} movies...")
        for i, movie in enumerate(movies, 1):
            print(f"Indexing movie {i}/{len(movies)}: {movie['title']}")
            # Add suggestion field
            movie['title_suggest'] = {
                'input': movie['title'],
                'weight': int(movie['vote_average'])
            }
            self.es.index(index=index_name, id=movie['id'], document=movie)
            
        return len(movies)

    def load_data(self):
        """Main method to load and index movie data"""
        print("Fetching popular movies...")
        movies = self.fetch_popular_movies()
        
        if not movies:
            print("No movies fetched. Please check your TMDb API key.")
            return
            
        print("Processing movie details...")
        processed_movies = self.process_movie_data(movies)
        
        if not processed_movies:
            print("No movies processed. Please check the API responses above.")
            return
            
        print("Indexing movies in Elasticsearch...")
        num_indexed = self.index_movies(processed_movies)
        
        print(f"Successfully indexed {num_indexed} movies")

if __name__ == "__main__":
    try:
        loader = MovieDataLoader()
        loader.load_data()
    except Exception as e:
        print(f"Error: {str(e)}")

