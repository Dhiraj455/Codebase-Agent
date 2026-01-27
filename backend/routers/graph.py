"""
Graph Router

Handles dependency graph endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from models.schemas import GraphResponse


def get_services(request: Request) -> Dict[str, Any]:
    """Dependency to get services from request state."""
    return request.state.services


router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
async def get_dependency_graph(
    repo_name: str = Query(..., description="Repository name"),
    analysis_id: Optional[str] = Query(None, description="Analysis ID (optional)"),
    services: Dict[str, Any] = Depends(get_services),
):
    """
    Get dependency graph for a repository.
    
    Returns the dependency graph with nodes, edges, cycles, and statistics.
    """
    try:
        # Get services
        dependency_graph_builder = services.get("dependency_graph_builder")
        repo_ingestion = services.get("repo_ingestion")

        if not dependency_graph_builder:
            raise HTTPException(
                status_code=503,
                detail="Dependency graph builder is not available",
            )

        # For now, we'll need to rebuild the graph from the repo
        # In a production system, you'd cache/store the graph
        # For this implementation, we'll return an error if the repo isn't cached
        
        # Try to find the repo in cache
        repo_cache_dir = repo_ingestion.cache_dir if repo_ingestion else None
        
        if not repo_cache_dir:
            raise HTTPException(
                status_code=503,
                detail="Repository ingestion service not available",
            )

        # Check if repo exists in cache
        import os
        from pathlib import Path
        
        repo_path = Path(repo_cache_dir) / repo_name
        
        if not repo_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{repo_name}' not found. Please analyze it first using /api/analyze",
            )

        # Get all code files from the repo (not just Python)
        all_code_files = repo_ingestion.extract_all_code_files(repo_path)
        
        if not all_code_files:
            # No code files found
            print(f"No code files found in {repo_name}. Returning empty graph.")
            graph_data = {
                "nodes": [],
                "edges": [],
                "cycles": [],
                "statistics": {
                    "nodes": 0,
                    "edges": 0,
                    "cycles": 0,
                    "density": 0,
                    "is_dag": True,
                    "message": "No code files found in repository"
                }
            }
        else:
            # Build dependency graph for all code files
            print(f"Building dependency graph for {repo_name} ({len(all_code_files)} code files)...")
            file_graph = dependency_graph_builder.build_file_dependency_graph(
                str(repo_path), all_code_files
            )

            # Export to JSON
            graph_data = dependency_graph_builder.export_graph_to_json(file_graph)

        return GraphResponse(
            nodes=graph_data.get("nodes", []),
            edges=graph_data.get("edges", []),
            cycles=graph_data.get("cycles", []),
            statistics=graph_data.get("statistics", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Graph retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dependency graph: {str(e)}",
        )
