

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

from services.repo_ingestion import RepoIngestionService
from services.code_analyzer import CodeAnalyzer
from services.dependency_graph import DependencyGraphBuilder
from services.chunking import CodeChunkingService
from services.embeddings import EmbeddingsService
from services.llm_reasoner import LLMReasoner
from services.code_smell_detector import CodeSmellDetector
from services.refactoring_advisor import RefactoringAdvisor


services: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Initializing services...")

    code_analyzer = CodeAnalyzer()
    dependency_graph_builder = DependencyGraphBuilder(code_analyzer=code_analyzer)

    llm_reasoner = None
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            if api_key.strip() and api_key != "your_gemini_api_key_here":
                model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
                llm_reasoner = LLMReasoner(api_key=api_key, model=model, code_analyzer=code_analyzer)
                print(f"LLM Reasoner (Gemini) initialized with model: {model}")
            else:
                print("Warning: GEMINI_API_KEY appears to be a placeholder. Please set a valid API key in backend/.env")
        else:
            print("Warning: GEMINI_API_KEY not set. LLM features will be disabled.")
            print(f"  Looking for .env file at: {env_path}")
            print(f"  .env file exists: {env_path.exists()}")
    except Exception as e:
        print(f"Warning: Failed to initialize LLM Reasoner: {e}")

    repo_ingestion = RepoIngestionService(
        cache_dir=os.getenv("REPO_CACHE_DIR", "./repos")
    )

    chunking_service = CodeChunkingService(code_analyzer=code_analyzer)

    embeddings_service = None
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key.strip() and api_key != "your_gemini_api_key_here":
            embeddings_service = EmbeddingsService(
                vector_store_path=os.getenv("VECTOR_STORE_PATH", "./vector_store"),
                api_key=api_key
            )
            print("Embeddings service (Gemini) initialized")
        else:
            print("Warning: GEMINI_API_KEY not set. Embeddings features will be disabled.")
    except Exception as e:
        print(f"Warning: Failed to initialize Embeddings Service: {e}")

    code_smell_detector = CodeSmellDetector(
        code_analyzer=code_analyzer,
        dependency_graph_builder=dependency_graph_builder,
        llm_reasoner=llm_reasoner,
    )

    refactoring_advisor = RefactoringAdvisor(
        code_smell_detector=code_smell_detector,
        llm_reasoner=llm_reasoner,
    )

    services["repo_ingestion"] = repo_ingestion
    services["code_analyzer"] = code_analyzer
    services["dependency_graph_builder"] = dependency_graph_builder
    services["chunking_service"] = chunking_service
    services["embeddings_service"] = embeddings_service
    services["llm_reasoner"] = llm_reasoner
    services["code_smell_detector"] = code_smell_detector
    services["refactoring_advisor"] = refactoring_advisor

    print("All services initialized successfully")

    yield

    print("Shutting down services...")


app = FastAPI(
    title="Codebase Analysis API",
    description="API for analyzing codebases, detecting code smells, and generating refactoring strategies",
    version="1.0.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def add_services_to_request(request: Request, call_next):

    request.state.services = services
    response = await call_next(request)
    return response

origins = [
    "http://localhost:3000",  # Next.js dev server
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):

    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors(),
            "status_code": 422,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):

    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "An unexpected error occurred",
            "status_code": 500,
        },
    )


@app.get("/")
async def root():

    return {
        "name": "Codebase Analysis API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "analyze": "/api/analyze",
            "ask": "/api/ask",
        },
    }


@app.get("/health")
async def health_check():

    health_status = {
        "status": "healthy",
        "api": "running",
        "services": {},
    }

    services_status = {}

    services_status["repo_ingestion"] = "available" if "repo_ingestion" in services else "unavailable"
    services_status["code_analyzer"] = "available" if "code_analyzer" in services else "unavailable"
    services_status["dependency_graph_builder"] = "available" if "dependency_graph_builder" in services else "unavailable"
    services_status["chunking_service"] = "available" if "chunking_service" in services else "unavailable"

    services_status["embeddings_service"] = "available" if services.get("embeddings_service") else "unavailable"
    services_status["llm_reasoner"] = "available" if services.get("llm_reasoner") else "unavailable"

    health_status["services"] = services_status

    critical_services = ["repo_ingestion", "code_analyzer", "dependency_graph_builder"]
    if all(services_status.get(svc) == "available" for svc in critical_services):
        health_status["status"] = "healthy"
    else:
        health_status["status"] = "degraded"
        health_status["message"] = "Some critical services are unavailable"

    return health_status


from routers import analyze, chat

app.include_router(analyze.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
