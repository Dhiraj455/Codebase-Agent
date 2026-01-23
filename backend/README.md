# Backend - Codebase Analysis API

FastAPI backend for codebase understanding and refactoring analysis.

## Setup

1. **Create and activate virtual environment:**

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file:**

   ```env
   OPENAI_API_KEY=your_api_key_here
   BACKEND_URL=http://localhost:8000
   VECTOR_STORE_PATH=./vector_store
   REPO_CACHE_DIR=./repos
   ```

4. **Run the server:**

   ```bash
   uvicorn main:app --reload --port 8000
   ```

## API Endpoints

- `POST /api/analyze` - Analyze a GitHub repository
- `POST /api/ask` - Ask questions about the codebase
- `GET /api/graph` - Get dependency graph

## Project Structure

```
backend/
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── models/
│   └── schemas.py       # Pydantic models
├── routers/
│   ├── analyze.py       # Analysis endpoints
│   ├── chat.py          # Chat/Q&A endpoints
│   └── graph.py         # Graph endpoints
├── services/
│   ├── repo_ingestion.py
│   ├── code_analyzer.py
│   ├── dependency_graph.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── llm_reasoner.py
│   ├── code_smell_detector.py
│   └── refactoring_advisor.py
└── utils/
```
