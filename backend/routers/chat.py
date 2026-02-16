

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from models.schemas import QuestionRequest, QuestionResponse


def get_services(request: Request) -> Dict[str, Any]:

    return request.state.services


router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    services: Dict[str, Any] = Depends(get_services),
):

    try:
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

        store_name = None
        if request.analysis_id:
            store_name = f"analysis_{request.analysis_id}"
        elif request.repo_name:
            store_name = request.repo_name
        else:
            raise HTTPException(
                status_code=400,
                detail="Either analysis_id or repo_name must be provided",
            )

        relevant_chunks = []
        try:
            print(f"Loading vector store '{store_name}'...")
            embeddings_service.load_vector_store(store_name)
            print(f" Vector store '{store_name}' loaded successfully")
            print(f"Searching for relevant chunks for: {request.question}")
            relevant_chunks = embeddings_service.similarity_search(
                request.question, k=5
            )
            print(f"Found {len(relevant_chunks)} relevant chunks")
        except FileNotFoundError as e:
            print(f" Vector store not found for '{store_name}': {e}")
            print("  Using LLM without RAG context.")
            relevant_chunks = []
        except Exception as e:
            print(f" Error loading vector store '{store_name}': {e}")
            print("  Using LLM without RAG context.")
            relevant_chunks = []

        print("Generating answer with LLM...")
        if relevant_chunks:
            answer = llm_reasoner.ask_question(
                question=request.question,
                relevant_chunks=relevant_chunks,
            )
        else:
            answer = llm_reasoner.ask_question_without_rag(
                question=request.question,
                repo_name=request.repo_name or store_name,
            )

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
