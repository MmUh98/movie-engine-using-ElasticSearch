# Context-Aware Movie Search Engine

A context-aware search engine that leverages user behavior and query history to deliver more relevant movie search results using Elasticsearch.

## Features

- Full-text search with Elasticsearch
- User session tracking for understanding query intent
- Context modeling based on previous queries
- Improved ranking using context-aware query rewriting
- Movie information with posters and summaries

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file with:
```
TMDB_API_KEY=your_tmdb_api_key
ELASTICSEARCH_URL=http://127.0.0.1:9200
ELASTICSEARCH_USER=elastic
ELASTICSEARCH_PASSWORD=your_password
```

3. Start Elasticsearch:
```bash
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=true" -e "ELASTIC_PASSWORD=your_password" docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

4. Run the application:
```bash
streamlit run app.py
```

## Project Structure

- `app.py`: Main Streamlit application
- `elasticsearch_client.py`: Elasticsearch connection and operations
- `data_loader.py`: TMDb API data fetching and processing
- `context_engine.py`: Context tracking and query enhancement
- `ranking.py`: Custom ranking implementation

## API Documentation

The search engine provides the following endpoints:
- `/search`: Main search endpoint with context awareness
- `/suggest`: Query suggestions based on context
- `/history`: User search history retrieval 