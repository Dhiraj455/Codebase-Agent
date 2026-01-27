"""
Analysis Router

Handles repository analysis endpoints.
"""

import os
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from models.schemas import AnalyzeRequest, AnalyzeResponse

# This will be injected from main.py
def get_services(request: Request) -> Dict[str, Any]:
    """Dependency to get services from request state."""
    return request.state.services


router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repository(
    request: AnalyzeRequest,
    services: Dict[str, Any] = Depends(get_services),
):
    """
    Analyze a GitHub repository.
    
    This endpoint performs a complete analysis:
    1. Clones the repository
    2. Analyzes code using AST
    3. Builds dependency graph
    4. Generates architecture summary
    5. Detects code smells
    6. Generates refactoring suggestions
    """
    try:
        # Get services
        repo_ingestion = services.get("repo_ingestion")
        code_analyzer = services.get("code_analyzer")
        dependency_graph_builder = services.get("dependency_graph_builder")
        chunking_service = services.get("chunking_service")
        embeddings_service = services.get("embeddings_service")
        llm_reasoner = services.get("llm_reasoner")
        code_smell_detector = services.get("code_smell_detector")
        refactoring_advisor = services.get("refactoring_advisor")

        if not all([repo_ingestion, code_analyzer, dependency_graph_builder]):
            raise HTTPException(
                status_code=503,
                detail="Required services are not available",
            )

        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        store_name = request.store_name or f"analysis_{analysis_id}"

        # Step 1: Clone repository
        print(f"Cloning repository: {request.repo_url}")
        repo_result = repo_ingestion.process_repo(request.repo_url)
        repo_path = repo_result["repo_path"]
        repo_name = repo_result["repo_name"]
        python_files = repo_result["files"]
        repo_structure = repo_result.get("repo_structure", {})

        # Get all code files (not just Python)
        all_code_files = repo_ingestion.extract_all_code_files(repo_path)
        has_python_files = len(python_files) > 0
        has_code_files = len(all_code_files) > 0
        
        if not has_code_files:
            raise HTTPException(
                status_code=400,
                detail=f"No code files found in repository. Detected languages: {', '.join(repo_structure.get('languages', ['Unknown']))}.",
            )

        # Step 2: Analyze all code files (Python and others)
        file_analyses = []
        if has_code_files:
            print(f"Analyzing {len(all_code_files)} code files (Python: {len(python_files)}, Others: {len(all_code_files) - len(python_files)})...")
            for file_info in all_code_files:
                try:
                    analysis = code_analyzer.analyze_file(file_info["absolute_path"])
                    file_analyses.append(analysis)
                except Exception as e:
                    print(f"⚠ Failed to analyze {file_info.get('path', 'unknown')}: {e}")
                    # Add error entry to maintain consistency
                    file_analyses.append({
                        "file_path": file_info.get("absolute_path", ""),
                        "file_name": file_info.get("name", "unknown"),
                        "language": code_analyzer._detect_language(file_info.get("absolute_path", "")),
                        "classes": [],
                        "functions": [],
                        "imports": [],
                        "module_variables": [],
                        "error": str(e),
                    })
        else:
            print("No code files found. Skipping code analysis.")

        # Step 3: Build dependency graph - use all code files
        dependency_graph_data = {"nodes": [], "edges": [], "cycles": [], "statistics": {}}
        if has_code_files:
            print("Building dependency graph...")
            try:
                file_graph = dependency_graph_builder.build_file_dependency_graph(
                    repo_path, all_code_files
                )
                dependency_graph_data = dependency_graph_builder.export_graph_to_json(file_graph)
            except Exception as e:
                print(f"⚠ Dependency graph building failed: {e}")
                # Continue with empty graph
        else:
            print("Skipping dependency graph (no code files).")

        # Step 4: Generate architecture summary (if LLM available)
        architecture_summary = {}
        if llm_reasoner:
            try:
                print("Generating architecture summary...")
                if has_code_files:
                    # Use detailed analysis with code analysis data (works for all languages now)
                    architecture_summary = llm_reasoner.analyze_codebase_architecture(
                        file_analyses, dependency_graph_data
                    )
                else:
                    # Use general analysis based on repo structure
                    print("Using LLM for general repository analysis...")
                    try:
                        architecture_summary = llm_reasoner.analyze_general_repository(
                            repo_structure, repo_path
                        )
                    except ValueError as e:
                        # API key or authentication error
                        error_msg = str(e)
                        print(f"LLM authentication error: {error_msg}")
                        raise HTTPException(
                            status_code=401,
                            detail=f"Google Gemini API authentication failed. Please check your GEMINI_API_KEY in backend/.env file. Error: {error_msg}",
                        )
                    except Exception as e:
                        # Other LLM errors
                        error_msg = str(e)
                        print(f"LLM analysis error: {error_msg}")
                        raise HTTPException(
                            status_code=502,
                            detail=f"LLM analysis failed: {error_msg}",
                        )
            except HTTPException:
                # Re-raise HTTP exceptions (like the ones above)
                raise
            except Exception as e:
                print(f"Architecture summary generation failed: {e}")
                architecture_summary = {
                    "error": "Architecture summary unavailable",
                    "message": str(e),
                }
        else:
            architecture_summary = {
                "error": "LLM not available",
                "message": "Google Gemini API key not configured",
            }

        # Step 5: Detect code smells (works for all languages now)
        code_smells = []
        if has_code_files:
            print("Detecting code smells...")
            try:
                code_smells = code_smell_detector.detect_code_smells(
                    file_analyses, dependency_graph_data
                )
                print(f"✓ Detected {len(code_smells)} code smells")
            except Exception as e:
                print(f"⚠ Code smell detection failed: {e}")
                import traceback
                traceback.print_exc()
                code_smells = []
                # Fallback to LLM if available
                if llm_reasoner:
                    print("Trying LLM-based code smell detection as fallback...")
                    try:
                        code_smells = llm_reasoner.detect_code_smells_general(
                            repo_structure, repo_path, architecture_summary
                        )
                        print(f"✓ Detected {len(code_smells)} code smells using LLM")
                    except Exception as e2:
                        print(f"⚠ LLM code smell detection also failed: {e2}")
        else:
            print("⚠ Skipping code smell detection (no code files).")

        # Step 6: Generate refactoring suggestions
        refactoring_strategies = []
        if refactoring_advisor:
            try:
                print("Generating refactoring strategies...")
                refactoring_strategies = refactoring_advisor.generate_refactoring_strategies(
                    code_smells, file_analyses
                )
            except Exception as e:
                print(f"Refactoring strategy generation failed: {e}")

        # Step 7: Create chunks and embeddings
        if embeddings_service:
            try:
                print(f"Creating code chunks and embeddings for store: {store_name}...")
                if has_code_files:
                    # Chunk all code files
                    chunks = []
                    python_file_paths = [f["absolute_path"] for f in python_files]
                    other_code_files = [f for f in all_code_files if f["absolute_path"] not in python_file_paths]
                    
                    # Chunk Python files using AST-based chunking
                    if python_file_paths:
                        python_chunks = chunking_service.chunk_multiple_files(python_file_paths)
                        chunks.extend(python_chunks)
                        print(f"Created {len(python_chunks)} chunks from {len(python_file_paths)} Python files")
                    
                    # Chunk other code files using text-based chunking
                    if other_code_files:
                        for file_info in other_code_files:
                            try:
                                file_chunks = chunking_service.chunk_text_file(file_info["absolute_path"])
                                chunks.extend(file_chunks)
                            except Exception as e:
                                print(f"⚠ Failed to chunk {file_info.get('path', 'unknown')}: {e}")
                        print(f"Created {len(chunks) - len(python_chunks) if python_file_paths else len(chunks)} chunks from {len(other_code_files)} non-Python code files")
                else:
                    chunks = []
                    print("No code files found to chunk.")
                
                if chunks:
                    print(f"Creating vector store '{store_name}' with {len(chunks)} chunks...")
                    embeddings_service.create_vector_store_from_chunks(chunks, store_name)
                    print(f"✓ Vector store '{store_name}' created successfully with {len(chunks)} chunks")
                else:
                    print("⚠ No chunks created. Skipping vector store creation.")
            except Exception as e:
                error_msg = str(e)
                # Check for API key related errors
                if "API key" in error_msg or "403" in error_msg or "leaked" in error_msg.lower():
                    print(f"⚠ Embeddings creation failed due to API key issue: {error_msg}")
                    print("  → The analysis will continue without vector store. Chat functionality may be limited.")
                    print("  → To fix: Update your GEMINI_API_KEY in backend/.env with a valid API key.")
                else:
                    print(f"❌ Embeddings creation failed: {error_msg}")
                    import traceback
                    traceback.print_exc()
                # Continue with analysis even if embeddings fail
        else:
            print("⚠ Embeddings service not available. Vector store will not be created.")
            print("  (This is normal if GEMINI_API_KEY is not set)")

        # Calculate statistics from all analyzed files
        print("Calculating statistics...")
        total_code_files = len(all_code_files)
        print(f"Found {total_code_files} total code files")

        # Calculate statistics from all file analyses (all languages)
        total_classes = sum(len(a.get("classes", [])) for a in file_analyses)
        total_functions = sum(len(a.get("functions", [])) for a in file_analyses)
        total_imports = sum(len(a.get("imports", [])) for a in file_analyses)
        
        print(f"✓ Statistics: {total_classes} classes, {total_functions} functions, {total_imports} imports")

        statistics = {
            "files_analyzed": total_code_files,  # Count all code files, not just Python
            "total_files": repo_structure.get("total_files", 0),
            "languages": repo_structure.get("languages", []),
            "total_classes": total_classes,
            "total_functions": total_functions,
            "total_imports": total_imports,
            "code_smells_count": len(code_smells),
            "refactoring_strategies_count": len(refactoring_strategies),
            "dependency_graph_nodes": dependency_graph_data.get("statistics", {}).get(
                "nodes", 0
            ),
            "dependency_graph_edges": dependency_graph_data.get("statistics", {}).get(
                "edges", 0
            ),
            "has_python_files": has_python_files,
            "has_code_files": has_code_files,
        }
        print(f"✓ Statistics calculated: {statistics['files_analyzed']} files, {statistics['code_smells_count']} code smells")

        # Generate project description (if LLM available)
        project_description = ""
        if llm_reasoner:
            try:
                print("Generating project description...")
                project_description = llm_reasoner.generate_project_description(
                    repo_structure, repo_path, architecture_summary
                )
                if project_description:
                    print(f"✓ Project description generated: {project_description[:100]}...")
                else:
                    print("⚠ Project description generation returned empty")
            except Exception as e:
                print(f"⚠ Project description generation failed: {e}")
                import traceback
                traceback.print_exc()
                project_description = ""

        # Verify vector store was created (if embeddings service was available)
        vector_store_created = False
        if embeddings_service:
            try:
                # Check if store exists
                store_info = embeddings_service.get_store_info(store_name)
                vector_store_created = store_info.get("exists", False)
                if vector_store_created:
                    print(f"✓ Verified: Vector store '{store_name}' exists at {store_info.get('path')}")
                else:
                    print(f"⚠ Warning: Vector store '{store_name}' was not created")
            except Exception as e:
                print(f"⚠ Could not verify vector store: {e}")

        # Add project description to architecture summary (always include, even if empty)
        if isinstance(architecture_summary, dict):
            # Always set project_description at top level
            architecture_summary["project_description"] = project_description
            # Also add to nested structure if it exists
            if "architecture_summary" in architecture_summary:
                if isinstance(architecture_summary["architecture_summary"], dict):
                    architecture_summary["architecture_summary"]["project_description"] = project_description
        
        print(f"\n{'='*60}")
        print(f"✓ Analysis complete for {repo_name}")
        print(f"  - Files analyzed: {statistics['files_analyzed']}")
        print(f"  - Code smells: {statistics['code_smells_count']}")
        print(f"  - Refactoring strategies: {statistics['refactoring_strategies_count']}")
        print(f"  - Vector store: {'✓ Created' if vector_store_created else '✗ Not created'}")
        print(f"{'='*60}\n")
        
        return AnalyzeResponse(
            success=True,
            repo_name=repo_name,
            analysis_id=analysis_id,
            file_count=total_code_files,  # Return all code files count
            architecture_summary=architecture_summary,
            code_smells=code_smells,
            refactoring_strategies=refactoring_strategies,
            dependency_graph=dependency_graph_data,
            statistics=statistics,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Analysis failed: {e}")
        print(f"Traceback:\n{error_trace}")
        # In debug mode, include full traceback
        detail = str(e)
        if os.getenv("DEBUG", "false").lower() == "true":
            detail = f"{str(e)}\n\nTraceback:\n{error_trace}"
        print(f"Detail: {detail}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {detail}",
        )
