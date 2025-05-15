import streamlit as st
import os
from elasticsearch_client import ElasticsearchClient
from context_engine import ContextEngine
from dotenv import load_dotenv
import requests
from PIL import Image
from io import BytesIO

load_dotenv()

# Initialize clients
es_client = ElasticsearchClient()
context_engine = ContextEngine()

# Set page config
st.set_page_config(
    page_title="Context-Aware Movie Search",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS for dark theme
st.markdown("""
    <style>
    body, .main, .block-container {
        background-color: #181818 !important;
        color: #f5f5f5 !important;
    }
    .stTextInput>div>div>input {
        background-color: #222 !important;
        color: #fff !important;
        border: 2px solid #e50914 !important;
    }
    .stButton>button {
        width: 100%;
        background-color: #e50914 !important;
        color: #fff !important;
        border-radius: 5px;
        border: none;
    }
    .movie-card {
        background-color: #222 !important;
        color: #fff !important;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.5);
        margin-bottom: 20px;
    }
    h3, p, strong, .movie-card * {
        color: #fff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("🎬 Context-Aware Movie Search")
st.markdown("Search for movies with context-aware results based on your search history")

# Sidebar
with st.sidebar:
    st.header("Search History")
    
    # Display search history
    if context_engine.movie_history:
        st.markdown("### Recent Searches")
        for query in context_engine.movie_history:
            st.markdown(f"- {query['query']}")
    
    if st.button("Clear History"):
        context_engine.clear_history()
        st.experimental_rerun()
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This search engine uses context from your previous searches to provide more relevant results.
    Try searching for related movies in sequence to see how the context affects the results!
    """)

# Search bar
query = st.text_input("Search for movies...", key="search")

# Get suggestions as you type
suggestions = []
if query:
    suggestions = es_client.suggest(query)

# Create a selectbox with suggestions if available
if suggestions:
    st.markdown("### Suggestions")
    for suggestion in suggestions:
        if st.button(suggestion, key=f"suggestion_{suggestion}"):
            query = suggestion
            st.experimental_rerun()

# Process search
if query:
    # Add query to context (with last movie if available)
    last_movie = None
    results = []
    context_terms = []
    context_entities = {'genres': [], 'cast': [], 'directors': []}

    # Get context entities from previous session
    if len(context_engine.movie_history) > 0:
        context_entities = context_engine.get_context_entities()

    # Get context terms
    context_terms = context_engine.get_context_terms()

    # Build and execute search query
    search_query = context_engine.build_elasticsearch_query(query, context_terms, context_entities)
    results = es_client.search(search_query)

    # Add query and the first result movie to context for next search
    if results:
        last_movie = results[0]['_source']
        context_engine.add_query(query, last_movie)
    else:
        context_engine.add_query(query)

    # Display results
    if results:
        st.markdown(f"### Found {len(results)} results")
        # Display context terms if any
        if context_terms:
            st.markdown("**Context terms:** " + ", ".join(context_terms))
        # Display context entities if any
        if any(context_entities.values()):
            st.markdown("**Context boost:** " + ", ".join(context_entities['genres'] + context_entities['cast'] + context_entities['directors']))
        # Display results in a grid
        cols = st.columns(3)
        for i, hit in enumerate(results):
            movie = hit['_source']
            col = cols[i % 3]
            with col:
                st.markdown(f"""
                <div class="movie-card">
                    <h3>{movie['title']}</h3>
                    <p><strong>Rating:</strong> {movie['vote_average']}/10</p>
                    <p><strong>Release Date:</strong> {movie['release_date']}</p>
                    <p><strong>Genres:</strong> {', '.join(movie['genres']) if movie['genres'] else 'N/A'}</p>
                    <p><strong>Director:</strong> {movie['director'] if movie['director'] else 'N/A'}</p>
                    <p><strong>Cast:</strong> {', '.join(movie['cast']) if movie['cast'] else 'N/A'}</p>
                    <p>{movie['overview'] if movie['overview'] else 'No overview available.'}</p>
                </div>
                """, unsafe_allow_html=True)
                if movie['poster_path']:
                    try:
                        response = requests.get(movie['poster_path'])
                        img = Image.open(BytesIO(response.content))
                        st.image(img, use_column_width=True)
                    except:
                        st.markdown("Poster not available")
    else:
        st.markdown("No results found")

# Display index stats
stats = es_client.get_index_stats()
st.sidebar.markdown("---")
st.sidebar.markdown("### Index Statistics")
st.sidebar.markdown(f"Total Movies: {stats['total_documents']}")
st.sidebar.markdown(f"Index Size: {stats['total_size'] / 1024 / 1024:.2f} MB") 