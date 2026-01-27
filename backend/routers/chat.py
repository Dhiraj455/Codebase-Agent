"""
Chat Router

Handles Q&A endpoints for asking questions about codebases.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from models.schemas import QuestionRequest, QuestionResponse


def get_services(request: Request) -> Dict[str, Any]:
    """Dependency to get services from request state."""
    return request.state.services


router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    services: Dict[str, Any] = Depends(get_services),
):
    """
    Ask a question about the codebase using RAG.
    
    Process:
    1. Retrieve relevant chunks using RAG
    2. Build context from chunks
    3. Query LLM with question + context
    """
    try:
        # Get services
        embeddings_service = services.get("embeddings_service")
        llm_reasoner = services.get("llm_reasoner")

        if not embeddings_service:
            raise HTTPException(
                status_code=503,
                detail="Embeddings service is not available",
            )

        if not llm_reasoner:
            raise HTTPException(
                status_code=503,
                detail="LLM service is not available. Google Gemini API key required.",
            )

        # Determine store name from analysis_id or repo_name
        store_name = None
        if request.analysis_id:
            # Try to load store by analysis_id
            store_name = f"analysis_{request.analysis_id}"
        elif request.repo_name:
            # Use repo_name directly
            store_name = request.repo_name
        else:
            raise HTTPException(
                status_code=400,
                detail="Either analysis_id or repo_name must be provided",
            )

        # Load vector store
        relevant_chunks = []
        try:
            print(f"Loading vector store '{store_name}'...")
            embeddings_service.load_vector_store(store_name)
            print(f"✓ Vector store '{store_name}' loaded successfully")
            # Step 1: Retrieve relevant chunks using RAG
            print(f"Searching for relevant chunks for: {request.question}")
            relevant_chunks = embeddings_service.similarity_search(
                request.question, k=5
            )
            print(f"Found {len(relevant_chunks)} relevant chunks")
        except FileNotFoundError as e:
            # Vector store doesn't exist - this can happen for non-Python repos
            # or if embeddings creation failed. Use LLM directly with repo context.
            print(f"⚠ Vector store not found for '{store_name}': {e}")
            print("  Using LLM without RAG context.")
            relevant_chunks = []
        except Exception as e:
            # Other errors loading vector store
            print(f"⚠ Error loading vector store '{store_name}': {e}")
            print("  Using LLM without RAG context.")
            relevant_chunks = []

        # Step 2: Query LLM with question + context (if available)
        print("Generating answer with LLM...")
        if relevant_chunks:
            # Use RAG-based Q&A
            answer = llm_reasoner.ask_question(
                question=request.question,
                relevant_chunks=relevant_chunks,
            )
        else:
            # No vector store available - use LLM directly with repo name context
            # This works for non-Python repos or when embeddings weren't created
            answer = llm_reasoner.ask_question_without_rag(
                question=request.question,
                repo_name=request.repo_name or store_name,
            )

        # Format sources (only if we have chunks)
        sources = []
        if relevant_chunks:
            sources = [
                {
                    "file": chunk["metadata"].get("file_name", "unknown"),
                    "chunk_type": chunk["metadata"].get("chunk_type", "unknown"),
                    "name": chunk["metadata"].get("name", "unknown"),
                    "score": chunk.get("score", 0),
                    "preview": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"],
                }
                for chunk in relevant_chunks
            ]
        else:
            # No RAG sources available (non-Python repo or vector store not created)
            sources = [{
                "file": "General knowledge",
                "chunk_type": "none",
                "name": "LLM general knowledge",
                "score": 0,
                "preview": "Answer generated without code context",
            }]

        return QuestionResponse(
            answer=answer,
            sources=sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Question answering failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to answer question: {str(e)}",
        )
