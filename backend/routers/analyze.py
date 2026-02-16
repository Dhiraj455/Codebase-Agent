import os
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from models.schemas import AnalyzeRequest, AnalyzeResponse

def get_services(request: Request) -> Dict[str, Any]:
    return request.state.services


router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repository(
    request: AnalyzeRequest,
    services: Dict[str, Any] = Depends(get_services),
):
    try:
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

        analysis_id = str(uuid.uuid4())
        store_name = request.store_name or f"analysis_{analysis_id}"

        print(f"Cloning repository: {request.repo_url}")
        repo_result = repo_ingestion.process_repo(request.repo_url)
        repo_path = repo_result["repo_path"]
        repo_name = repo_result["repo_name"]
        python_files = repo_result["files"]
        repo_structure = repo_result.get("repo_structure", {})

        all_code_files = repo_ingestion.extract_all_code_files(repo_path)
        has_python_files = len(python_files) > 0
        has_code_files = len(all_code_files) > 0
        
        if not has_code_files:
            raise HTTPException(
                status_code=400,
                detail=f"No code files found in repository. Detected languages: {', '.join(repo_structure.get('languages', ['Unknown']))}.",
            )

        file_analyses = []
        if has_code_files:
            print(f"Analyzing {len(all_code_files)} code files (Python: {len(python_files)}, Others: {len(all_code_files) - len(python_files)})...")
            successful_analyses = 0
            failed_analyses = 0
            for file_info in all_code_files:
                try:
                    analysis = code_analyzer.analyze_file(file_info["absolute_path"])
                    file_analyses.append(analysis)
                    successful_analyses += 1
                    if successful_analyses <= 3:
                        classes_count = len(analysis.get("classes", []))
                        functions_count = len(analysis.get("functions", []))
                        print(f"  Sample: {file_info.get('name', 'unknown')} - {classes_count} classes, {functions_count} functions")
                except Exception as e:
                    print(f"Failed to analyze {file_info.get('path', 'unknown')}: {e}")
                    failed_analyses += 1
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
            print(f"Analysis complete: {successful_analyses} successful, {failed_analyses} failed")
            
            total_classes = sum(len(a.get("classes", [])) for a in file_analyses if "error" not in a)
            total_functions = sum(len(a.get("functions", [])) for a in file_analyses if "error" not in a)
            print(f"  Total: {total_classes} classes, {total_functions} functions across all files")
        else:
            print("No code files found. Skipping code analysis.")

        dependency_graph_data = {"nodes": [], "edges": [], "cycles": [], "statistics": {}}
        if has_code_files:
            print("Building dependency graph...")
            try:
                file_graph = dependency_graph_builder.build_file_dependency_graph(
                    repo_path, all_code_files
                )
                dependency_graph_data = dependency_graph_builder.export_graph_to_json(file_graph)
            except Exception as e:
                print(f"Dependency graph building failed: {e}")
        else:
            print("Skipping dependency graph (no code files).")

        architecture_summary = {}
        if llm_reasoner:
            try:
                print("Generating architecture summary...")
                if has_code_files:
                    architecture_summary = llm_reasoner.analyze_codebase_architecture(
                        file_analyses, dependency_graph_data
                    )
                else:
                    print("Using LLM for general repository analysis...")
                    try:
                        architecture_summary = llm_reasoner.analyze_general_repository(
                            repo_structure, repo_path
                        )
                    except ValueError as e:
                        error_msg = str(e)
                        print(f"LLM authentication error: {error_msg}")
                        raise HTTPException(
                            status_code=401,
                            detail=f"Google Gemini API authentication failed. Please check your GEMINI_API_KEY in backend/.env file. Error: {error_msg}",
                        )
                    except Exception as e:
                        error_msg = str(e)
                        print(f"LLM analysis error: {error_msg}")
                        raise HTTPException(
                            status_code=502,
                            detail=f"LLM analysis failed: {error_msg}",
                        )
            except HTTPException:
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

        code_smells = []
        if has_code_files:
            print("Detecting code smells...")
            valid_analyses = [a for a in file_analyses if "error" not in a]
            print(f"  Processing {len(valid_analyses)} valid file analyses (out of {len(file_analyses)} total)")
            if valid_analyses:
                sample = valid_analyses[0]
                print(f"  Sample analysis: {sample.get('file_name', 'unknown')} - language: {sample.get('language', 'unknown')}, classes: {len(sample.get('classes', []))}, functions: {len(sample.get('functions', []))}")
            
            try:
                if code_smell_detector:
                    code_smells = code_smell_detector.detect_code_smells(
                        file_analyses, dependency_graph_data
                    )
                    print(f"Detected {len(code_smells)} code smells")
                    if code_smells:
                        print(f"  Sample smells: {[s.get('issue', 'unknown') for s in code_smells[:3]]}")
                else:
                    print("Code smell detector not available")
            except Exception as e:
                print(f"Code smell detection failed: {e}")
                import traceback
                traceback.print_exc()
                code_smells = []
                if llm_reasoner:
                    print("Trying LLM-based code smell detection as fallback...")
                    try:
                        code_smells = llm_reasoner.detect_code_smells_general(
                            repo_structure, repo_path, architecture_summary
                        )
                        print(f"Detected {len(code_smells)} code smells using LLM fallback")
                    except Exception as e2:
                        print(f"LLM code smell detection also failed: {e2}")
                        import traceback
                        traceback.print_exc()
        else:
            print("Skipping code smell detection (no code files).")

        refactoring_strategies = []
        if refactoring_advisor:
            try:
                print("Generating refactoring strategies...")
                if code_smells:
                    refactoring_strategies = refactoring_advisor.generate_refactoring_strategies(
                        code_smells, file_analyses
                    )
                    print(f"Generated {len(refactoring_strategies)} refactoring strategies")
                else:
                    print("No code smells found, skipping refactoring strategy generation")
            except Exception as e:
                print(f"Refactoring strategy generation failed: {e}")
                import traceback
                traceback.print_exc()
                refactoring_strategies = []

        if embeddings_service:
            try:
                print(f"Creating code chunks and embeddings for store: {store_name}...")
                if has_code_files:
                    chunks = []
                    python_file_paths = [f["absolute_path"] for f in python_files]
                    other_code_files = [f for f in all_code_files if f["absolute_path"] not in python_file_paths]
                    
                    print(f"  Chunking: {len(python_file_paths)} Python files, {len(other_code_files)} other code files")
                    
                    if python_file_paths:
                        try:
                            python_chunks = chunking_service.chunk_multiple_files(python_file_paths)
                            chunks.extend(python_chunks)
                            print(f"  Created {len(python_chunks)} chunks from {len(python_file_paths)} Python files")
                        except Exception as e:
                            print(f"  Failed to chunk Python files: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    if other_code_files:
                        other_chunks_count = 0
                        for file_info in other_code_files:
                            try:
                                file_chunks = chunking_service.chunk_text_file(file_info["absolute_path"])
                                chunks.extend(file_chunks)
                                other_chunks_count += len(file_chunks)
                            except Exception as e:
                                print(f"  Failed to chunk {file_info.get('path', 'unknown')}: {e}")
                        print(f"  Created {other_chunks_count} chunks from {len(other_code_files)} non-Python code files")
                else:
                    chunks = []
                    print("  No code files found to chunk.")
                
                if chunks:
                    print(f"  Creating vector store '{store_name}' with {len(chunks)} chunks...")
                    try:
                        embeddings_service.create_vector_store_from_chunks(chunks, store_name)
                        print(f"  Vector store '{store_name}' created successfully with {len(chunks)} chunks")
                    except Exception as e:
                        print(f"  Failed to create vector store: {e}")
                        import traceback
                        traceback.print_exc()
                        raise
                else:
                    print("  No chunks created. Skipping vector store creation.")
            except Exception as e:
                error_msg = str(e)
                if "API key" in error_msg or "403" in error_msg or "leaked" in error_msg.lower() or "PermissionDenied" in error_msg:
                    print(f"  Embeddings creation failed due to API key issue: {error_msg}")
                    print("  The analysis will continue without vector store. Chat functionality may be limited.")
                    print("  To fix: Update your GEMINI_API_KEY in backend/.env with a valid API key.")
                else:
                    print(f"  Embeddings creation failed: {error_msg}")
                    import traceback
                    traceback.print_exc()
        else:
            print("Embeddings service not available. Vector store will not be created.")
            print("  (This is normal if GEMINI_API_KEY is not set)")

        print("Calculating statistics...")
        total_code_files = len(all_code_files)
        print(f"Found {total_code_files} total code files")

        total_classes = sum(len(a.get("classes", [])) for a in file_analyses)
        total_functions = sum(len(a.get("functions", [])) for a in file_analyses)
        total_imports = sum(len(a.get("imports", [])) for a in file_analyses)
        
        print(f"Statistics: {total_classes} classes, {total_functions} functions, {total_imports} imports")

        statistics = {
            "files_analyzed": total_code_files,
            "total_files": repo_structure.get("total_files", 0),
            "languages": repo_structure.get("languages", []),
            "total_classes": total_classes,
            "total_functions": total_functions,
            "total_imports": total_imports,
            "code_smells_count": len(code_smells),
            "refactoring_strategies_count": len(refactoring_strategies),
            "has_python_files": has_python_files,
            "has_code_files": has_code_files,
        }
        print(f"Statistics calculated: {statistics['files_analyzed']} files, {statistics['code_smells_count']} code smells")

        project_description = ""
        if llm_reasoner:
            try:
                print("Generating project description...")
                project_description = llm_reasoner.generate_project_description(
                    repo_structure, repo_path, architecture_summary
                )
                if project_description:
                    print(f"Project description generated ({len(project_description)} chars)")
                else:
                    print("Project description generation returned empty")
            except Exception as e:
                print(f"Project description generation failed: {e}")
                import traceback
                traceback.print_exc()
                project_description = ""
        else:
            print("LLM reasoner not available, skipping project description generation")

        vector_store_created = False
        if embeddings_service:
            try:
                store_info = embeddings_service.get_store_info(store_name)
                vector_store_created = store_info.get("exists", False)
                if vector_store_created:
                    print(f"Verified: Vector store '{store_name}' exists at {store_info.get('path')}")
                else:
                    print(f"Warning: Vector store '{store_name}' was not created")
            except Exception as e:
                print(f"Could not verify vector store: {e}")

        if isinstance(architecture_summary, dict):
            architecture_summary["project_description"] = project_description
            if "architecture_summary" in architecture_summary:
                if isinstance(architecture_summary["architecture_summary"], dict):
                    architecture_summary["architecture_summary"]["project_description"] = project_description
        
        print(f"\n{'='*60}")
        print(f"Analysis complete for {repo_name}")
        print(f"  - Files analyzed: {statistics['files_analyzed']}")
        print(f"  - Code smells: {statistics['code_smells_count']}")
        print(f"  - Refactoring strategies: {statistics['refactoring_strategies_count']}")
        print(f"  - Vector store: {'Created' if vector_store_created else 'Not created'}")
        print(f"{'='*60}\n")
        
        return AnalyzeResponse(
            success=True,
            repo_name=repo_name,
            analysis_id=analysis_id,
            file_count=total_code_files,
            architecture_summary=architecture_summary,
            code_smells=code_smells,
            refactoring_strategies=refactoring_strategies,
            statistics=statistics,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Analysis failed: {e}")
        print(f"Traceback:\n{error_trace}")
        detail = str(e)
        if os.getenv("DEBUG", "false").lower() == "true":
            detail = f"{str(e)}\n\nTraceback:\n{error_trace}"
        print(f"Detail: {detail}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {detail}",
        )
