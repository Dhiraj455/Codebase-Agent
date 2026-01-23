# 🚀 Codebase Understanding & Refactoring Agent - Implementation Plan

## 📊 Current Status

✅ **Completed:**
- Next.js 16 + TypeScript project initialized
- Tailwind CSS v4 installed
- Basic project structure in place

❌ **Not Started:**
- Backend (Python/FastAPI)
- Frontend dependencies (axios, react-flow-renderer)
- All core features

---

## 🎯 What Needs to Be Done

### **PHASE 1: Project Setup** (Foundation)

#### 1.1 Frontend Dependencies
- [ ] Install `axios` for API calls
- [ ] Install `react-flow-renderer` (or `reactflow`) for graph visualization
- [ ] Verify Tailwind is properly configured

#### 1.2 Backend Setup
- [ ] Create `backend/` directory
- [ ] Set up Python virtual environment
- [ ] Create `requirements.txt` with all dependencies:
  - FastAPI, uvicorn
  - gitpython (repo cloning)
  - ast, radon (code analysis)
  - networkx (dependency graphs)
  - faiss-cpu (vector store)
  - langchain, openai (LLM integration)
  - pydantic (data validation)

---

### **PHASE 2: Backend Core** (Most Critical)

#### 2.1 GitHub Repo Ingestion
**File:** `backend/services/repo_ingestion.py`
- [ ] Clone repository from URL
- [ ] Filter files (ignore `.git`, `venv`, `node_modules`, `__pycache__`)
- [ ] Extract only Python files (per Phase 0 scope)
- [ ] Return file list with paths

#### 2.2 Static Code Analysis (AST)
**File:** `backend/services/code_analyzer.py`
- [ ] Parse Python files using `ast` module
- [ ] Extract:
  - Classes (name, methods, docstrings)
  - Functions (name, parameters, docstrings)
  - Imports (what's imported, from where)
  - Module-level variables
- [ ] Calculate complexity using `radon`
- [ ] Return structured JSON per file

#### 2.3 Dependency Graph Builder
**File:** `backend/services/dependency_graph.py`
- [ ] Build file-level dependency graph (imports)
- [ ] Build function-level call graph (optional, advanced)
- [ ] Use NetworkX for graph structure
- [ ] Detect circular dependencies
- [ ] Export graph as JSON (nodes + edges)

#### 2.4 Code Chunking Strategy
**File:** `backend/services/chunking.py`
- [ ] Chunk rules:
  - One class per chunk (with its methods)
  - One module-level function group per chunk
  - Include imports + docstrings in context
- [ ] Store metadata:
  - File path
  - Chunk type (class/function/module)
  - Class/function name
  - Line numbers
- [ ] Return list of chunks with metadata

#### 2.5 Embeddings + Vector Store
**File:** `backend/services/embeddings.py`
- [ ] Initialize OpenAI embeddings (or open-source alternative)
- [ ] Create FAISS vector store from chunks
- [ ] Store metadata with each embedding
- [ ] Implement similarity search function
- [ ] Save/load vector store to disk

---

### **PHASE 3: LLM Reasoning Layer**

#### 3.1 Architecture Summary Generator
**File:** `backend/services/llm_reasoner.py`
- [ ] Design prompt template for architecture analysis
- [ ] Include:
  - Code structure summary
  - Dependency graph
  - Complexity metrics
- [ ] Use structured output (JSON) from LLM
- [ ] Parse and validate response
- [ ] Return: architecture type, key modules, data flow, risks

#### 3.2 Code Smell Detection
**File:** `backend/services/code_smell_detector.py`
- [ ] Combine AST metrics (complexity, size) with LLM analysis
- [ ] Detect:
  - God classes (too many responsibilities)
  - High cyclomatic complexity
  - Circular dependencies
  - Missing docstrings
  - Tight coupling
- [ ] Return prioritized list of issues

#### 3.3 Refactoring Strategy Generator
**File:** `backend/services/refactoring_advisor.py`
- [ ] Generate incremental refactoring suggestions
- [ ] **Important:** Do NOT rewrite code, only suggest steps
- [ ] Include:
  - Issue description
  - Severity (high/medium/low)
  - Suggested steps (ordered)
  - Risk assessment
  - Estimated effort
- [ ] Return structured JSON

---

### **PHASE 4: API Design (FastAPI)**

#### 4.1 FastAPI Application Setup
**File:** `backend/main.py`
- [ ] Initialize FastAPI app
- [ ] Set up CORS for Next.js frontend
- [ ] Configure error handling
- [ ] Add health check endpoint

#### 4.2 API Endpoints
**File:** `backend/routers/analyze.py`, `backend/routers/chat.py`, `backend/routers/graph.py`

**POST `/api/analyze`**
- [ ] Input: `{ "repo_url": "https://github.com/..." }`
- [ ] Process:
  1. Clone repo
  2. Analyze code (AST)
  3. Build dependency graph
  4. Generate architecture summary
  5. Detect code smells
  6. Generate refactoring suggestions
- [ ] Output: Complete analysis JSON

**POST `/api/ask`**
- [ ] Input: `{ "question": "...", "analysis_id": "..." }`
- [ ] Process:
  1. Retrieve relevant chunks using RAG
  2. Build context from chunks
  3. Query LLM with question + context
- [ ] Output: `{ "answer": "..." }`

**GET `/api/graph`**
- [ ] Input: `{ "analysis_id": "..." }`
- [ ] Output: Dependency graph JSON (nodes + edges)

#### 4.3 Data Models
**File:** `backend/models/schemas.py`
- [ ] Pydantic models for:
  - AnalysisRequest
  - AnalysisResponse
  - QuestionRequest
  - QuestionResponse
  - GraphResponse
  - CodeSmell
  - RefactoringSuggestion

---

### **PHASE 5: Frontend (Next.js)**

#### 5.1 Project Structure
```
codebase-agent/
├── app/
│   ├── page.tsx          # Home (repo input)
│   ├── analysis/
│   │   └── page.tsx      # Analysis results
│   ├── graph/
│   │   └── page.tsx      # Dependency graph
│   ├── chat/
│   │   └── page.tsx      # Q&A interface
│   └── api/
│       └── proxy/        # Next.js API routes (proxy to backend)
```

#### 5.2 Home Page (`/`)
**File:** `app/page.tsx`
- [ ] Repo URL input form
- [ ] Submit button
- [ ] Loading state
- [ ] Error handling
- [ ] Redirect to `/analysis` on success

#### 5.3 Analysis Page (`/analysis`)
**File:** `app/analysis/page.tsx`
- [ ] Display architecture summary
- [ ] Show code smells (prioritized list)
- [ ] Display refactoring suggestions
- [ ] Link to `/graph` and `/chat`
- [ ] Modern, clean UI with Tailwind

#### 5.4 Graph Page (`/graph`)
**File:** `app/graph/page.tsx`
- [ ] React Flow integration
- [ ] Render nodes (files) and edges (dependencies)
- [ ] Interactive (zoom, pan, select)
- [ ] Highlight circular dependencies
- [ ] Node details on click

#### 5.5 Chat Page (`/chat`)
**File:** `app/chat/page.tsx`
- [ ] Chat interface (input + message history)
- [ ] Send questions about codebase
- [ ] Display LLM responses
- [ ] Loading states

#### 5.6 API Integration
**File:** `app/api/proxy/route.ts` (or separate files)
- [ ] Next.js API routes that proxy to FastAPI backend
- [ ] Handle CORS
- [ ] Error handling
- [ ] Type-safe with TypeScript

---

### **PHASE 6: Configuration & Environment**

#### 6.1 Environment Variables
**File:** `.env.local` (frontend), `backend/.env` (backend)
- [ ] OpenAI API key (or alternative LLM)
- [ ] Backend URL
- [ ] Vector store path
- [ ] Repo cache directory

#### 6.2 Configuration Files
- [ ] `backend/config.py` - Settings management
- [ ] `.gitignore` - Exclude venv, cache, .env files

---

## 🏗️ Recommended Folder Structure

```
GenAIAgent/
├── codebase-agent/          # Next.js frontend
│   ├── app/
│   ├── public/
│   ├── package.json
│   └── ...
├── backend/                 # Python FastAPI backend
│   ├── venv/
│   ├── main.py
│   ├── requirements.txt
│   ├── config.py
│   ├── models/
│   │   └── schemas.py
│   ├── routers/
│   │   ├── analyze.py
│   │   ├── chat.py
│   │   └── graph.py
│   ├── services/
│   │   ├── repo_ingestion.py
│   │   ├── code_analyzer.py
│   │   ├── dependency_graph.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── llm_reasoner.py
│   │   ├── code_smell_detector.py
│   │   └── refactoring_advisor.py
│   └── utils/
│       └── ...
└── IMPLEMENTATION_PLAN.md
```

---

## 🚦 Implementation Order (Recommended)

1. **Phase 1** → Set up dependencies and folder structure
2. **Phase 2.1-2.2** → Repo ingestion + AST analysis (get basic data)
3. **Phase 4.1-4.2** → Basic FastAPI endpoint to test
4. **Phase 5.1-5.2** → Frontend home page + API integration
5. **Phase 2.3-2.5** → Dependency graph + chunking + embeddings
6. **Phase 3** → LLM reasoning layer
7. **Phase 5.3-5.5** → Complete frontend pages
8. **Phase 6** → Polish and configuration

---

## 🔑 Key Design Decisions

1. **Language Support:** Start with Python ONLY (per Phase 0)
2. **LLM Choice:** Decide between OpenAI API vs open-source (Ollama, etc.)
3. **Vector Store:** FAISS for local, or consider Pinecone/Weaviate for production
4. **Caching:** Cache cloned repos and analysis results
5. **Error Handling:** Robust error handling at every layer

---

## 📝 Next Steps

**Tell me which phase/component you want to start with, and I'll implement it!**

Recommended starting points:
- **Option A:** Phase 1 (setup) + Phase 2.1 (repo ingestion) - Get basic structure working
- **Option B:** Phase 4 (FastAPI) + Phase 5.2 (frontend) - Get end-to-end flow working first
- **Option C:** Phase 2.2 (AST analysis) - Core functionality first
