import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

class ElasticsearchClient:
    def __init__(self):
        self.es = Elasticsearch(
            os.getenv('ELASTICSEARCH_URL'),
            basic_auth=(os.getenv('ELASTICSEARCH_USER'), os.getenv('ELASTICSEARCH_PASSWORD')),
            verify_certs=False
        )
        self.index_name = "movies"

    def search(self, query_body):
        """Execute search query"""
        try:
            response = self.es.search(
                index=self.index_name,
                body=query_body
            )
            return response['hits']['hits']
        except Exception as e:
            print(f"Error executing search: {str(e)}")
            return []

    def get_movie(self, movie_id):
        """Get a specific movie by ID"""
        try:
            response = self.es.get(
                index=self.index_name,
                id=movie_id
            )
            return response['_source']
        except Exception as e:
            print(f"Error getting movie: {str(e)}")
            return None

    def suggest(self, query, size=5):
        """Get search suggestions"""
        try:
            response = self.es.search(
                index=self.index_name,
                body={
                    "suggest": {
                        "title_suggest": {
                            "prefix": query,
                            "completion": {
                                "field": "title_suggest",
                                "size": size,
                                "skip_duplicates": True
                            }
                        }
                    }
                }
            )
            return [hit['text'] for hit in response['suggest']['title_suggest'][0]['options']]
        except Exception as e:
            print(f"Error getting suggestions: {str(e)}")
            return []

    def get_index_stats(self):
        """Get index statistics"""
        try:
            stats = self.es.indices.stats(index=self.index_name)
            return {
                'total_documents': stats['indices'][self.index_name]['total']['docs']['count'],
                'total_size': stats['indices'][self.index_name]['total']['store']['size_in_bytes']
            }
        except Exception as e:
            print(f"Error getting index stats: {str(e)}")
            return {'total_documents': 0, 'total_size': 0} 