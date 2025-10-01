# Personal Knowledge Graph Construction Agent

## Overview

A lightweight Personal Knowledge Graph (PKG) system designed to run on Replit Free tier. The system ingests plain text and Markdown files, extracts entities and relationships using rule-based methods, and stores them in an RDF graph with full provenance tracking. It provides semantic search capabilities using either OpenAI embeddings (when API key is available) or TF-IDF fallback, and exposes a FastAPI-based REST API with a simple web UI.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Philosophy

**Resource-Constrained Operation**: All architectural decisions prioritize minimal resource usage to run on Replit Free tier. No heavy transformer models, no external databases, and single-process execution only.

**Provenance-First Approach**: Every triple extracted from text maintains full provenance (source file, text snippet, character offsets) to enable citation and verification of knowledge.

### Application Layer

**FastAPI Single-Process Architecture**: Uses FastAPI with Uvicorn in a single-process mode without background workers or async task queues. All ingestion happens synchronously within API request handlers to avoid complexity and resource overhead. Simple job tracking uses in-memory objects rather than persistent job queues.

**Stateless API Design**: REST endpoints follow standard patterns:
- POST /ingest for file upload and processing
- POST /query for semantic search
- GET /entity/{id} for entity retrieval
- GET /jobs/{id} for ingestion job status

**Minimal Frontend**: Single-page HTML with inline CSS/JavaScript served directly from Python, avoiding build tools, bundlers, or separate frontend processes.

### Knowledge Extraction Pipeline

**Rule-Based + Regex Extraction**: Avoids heavy NLP libraries (spaCy, Transformers) in favor of simple patterns:
- Sentence splitting using basic punctuation rules
- Pattern matching for common relationship templates (X is a Y, X works on Y)
- Capitalization-based entity detection
- No external model downloads or GPU requirements

**Chunking Strategy**: Text is split into overlapping chunks (300 words with 50-word overlap) to maintain context across boundaries while keeping memory usage low.

**Confidence Scoring**: Simple rule-based confidence scores (0.8 for pattern matches) rather than learned models.

### Data Persistence Layer

**RDFLib Triple Store**: Uses RDFLib with Turtle serialization format stored in `data/graph.ttl`. Choice rationale:
- Pure Python implementation (no external database process)
- Standard RDF semantics for knowledge representation
- File-based persistence survives Replit container restarts
- Lightweight query capabilities via SPARQL-like patterns

**Separate Provenance Store**: Provenance data stored in `data/provenance.json` rather than as RDF annotations. This separation simplifies:
- Provenance lookups by triple key
- JSON serialization/deserialization
- Avoiding RDF reification complexity

**Entity Aliasing**: `data/aliases.json` maintains canonical entity mappings for deduplication (e.g., "Bob" and "Robert" → same entity).

### Semantic Search Architecture

**Dual Embedding Strategy**: 
- **OpenAI Mode**: When `OPENAI_API_KEY` environment variable is set, uses `text-embedding-3-small` model for high-quality embeddings
- **Fallback Mode**: Uses scikit-learn TfidfVectorizer for local, zero-cost embeddings when OpenAI unavailable

**Rationale**: Allows both high-quality search (when API credits available) and completely offline operation (for free/demo usage).

**Vector Storage**: Embeddings stored as NumPy arrays in `data/vectors.npy` with metadata in `data/vector_metadata.json`. Avoids heavy vector databases (FAISS, Chroma) that would exceed memory limits.

**Similarity Search**: Cosine similarity computed via scikit-learn, returning top-k results with provenance snippets.

### File Organization Strategy

**Modular Component Separation**:
- `main.py`: FastAPI app initialization only
- `api_routes.py`: All HTTP endpoint handlers
- `graph_store.py`: RDF graph and provenance management
- `embeddings.py`: Embedding generation and search
- `ingest.py`: Text chunking and extraction logic
- `ui.py`: Frontend HTML generation

**Data Directory**: All persistent state in `data/` subdirectory for easy backup and version control exclusion.

**Sample Data**: Pre-loaded example files in `sample_data/` for testing and demonstration.

### Error Handling Philosophy

**Graceful Degradation**: System continues operating when non-critical components fail:
- Missing OpenAI key → falls back to TF-IDF
- Unicode decode errors → skip file, continue processing
- Missing data files → initialize empty structures

**Minimal Logging**: Simple print statements rather than structured logging to reduce dependencies.

## External Dependencies

### Python Packages

**FastAPI + Uvicorn**: Web framework and ASGI server chosen for lightweight async capabilities and automatic OpenAPI documentation generation.

**RDFLib**: Pure Python RDF library for triple storage. No external database process required.

**NumPy + scikit-learn**: Minimal scientific computing stack for TF-IDF vectorization and cosine similarity. These are widely cached on Replit.

**python-multipart**: Required for FastAPI file upload handling via multipart/form-data.

**httpx**: HTTP client for potential future web page fetching capabilities.

**OpenAI (optional)**: Official OpenAI Python client for embedding generation when API key is provided.

### External Services

**OpenAI API (Optional)**: Text embedding service using `text-embedding-3-small` model. Only used when `OPENAI_API_KEY` environment variable is configured. System fully functional without it using TF-IDF fallback.

### Storage Mechanisms

**Local File System**: All data persisted to disk in project `data/` directory:
- `graph.ttl`: RDF triples in Turtle format
- `provenance.json`: Triple provenance metadata
- `aliases.json`: Entity alias mappings
- `vectors.npy`: NumPy vector embeddings
- `vector_metadata.json`: Vector-to-triple mappings
- `tfidf_vectorizer.pkl`: Pickled TF-IDF model (when in fallback mode)

**No External Databases**: Deliberately avoids PostgreSQL, MongoDB, Redis, or other database processes to minimize resource usage and deployment complexity.