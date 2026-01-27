"""
LLM Reasoning Service

Uses LLM to analyze codebase architecture, detect patterns, and generate insights.
"""

import os
import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ValidationError

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .code_analyzer import CodeAnalyzer
from .dependency_graph import DependencyGraphBuilder


class ArchitectureSummary(BaseModel):
    """Structured output model for architecture summary."""

    architecture_type: str = Field(
        description="Type of architecture (e.g., 'Layered', 'Microservices', 'MVC', 'Monolithic', 'Service-Oriented')"
    )
    key_modules: List[str] = Field(
        description="List of key module names that form the core of the system"
    )
    data_flow: str = Field(
        description="Description of how data flows through the system"
    )
    risks: List[Dict[str, str]] = Field(
        description="List of identified risks, each with 'severity' (high/medium/low) and 'description'"
    )
    strengths: List[str] = Field(
        default=[],
        description="List of architectural strengths or good practices observed"
    )
    recommendations: List[str] = Field(
        default=[],
        description="High-level recommendations for improvement"
    )


class CodeSmellResult(BaseModel):
    """Structured output model for code smell detection."""

    issue: str = Field(description="Name of the code smell or issue")
    severity: str = Field(description="Severity level: high, medium, or low")
    description: str = Field(description="Detailed description of the issue")
    location: str = Field(description="File or module where the issue is found")
    impact: str = Field(description="Impact of this issue on the codebase")


class LLMReasoner:
    """Service for LLM-based code analysis and reasoning."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp",
        code_analyzer: Optional[CodeAnalyzer] = None,
        dependency_graph_builder: Optional[DependencyGraphBuilder] = None,
    ):
        """
        Initialize the LLM reasoner.

        Args:
            api_key: Google Gemini API key. If None, reads from GEMINI_API_KEY env var.
            model: Gemini model to use (default: gemini-2.0-flash-exp)
            code_analyzer: Optional CodeAnalyzer instance
            dependency_graph_builder: Optional DependencyGraphBuilder instance
        """
        if genai is None:
            raise ImportError(
                "Google Generative AI library not installed. Install with: pip install google-generativeai"
            )

        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Google Gemini API key required. Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model_name = model
        
        # Map model names to correct Gemini API format
        # Remove "models/" prefix if present, and use correct model identifier
        model_mapping = {
            "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
            "gemini-1.5-pro": "gemini-1.5-pro",
            "gemini-1.5-flash": "gemini-1.5-flash",
            "gemini-pro": "gemini-pro",
        }
        
        # Use mapped name or original if not in mapping
        api_model_name = model_mapping.get(model, model)
        
        # Remove "models/" prefix if user included it
        if api_model_name.startswith("models/"):
            api_model_name = api_model_name.replace("models/", "")
        
        try:
            self.model = genai.GenerativeModel(api_model_name)
        except Exception as e:
            # Try alternative model names if the specified one fails
            print(f"Warning: Model {api_model_name} not available, trying gemini-2.0-flash-exp...")
            try:
                self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
                self.model_name = "gemini-2.0-flash-exp"
            except Exception:
                # Try gemini-1.5-flash
                print(f"Warning: gemini-2.0-flash-exp not available, trying gemini-1.5-flash...")
                try:
                    self.model = genai.GenerativeModel("gemini-1.5-flash")
                    self.model_name = "gemini-1.5-flash"
                except Exception:
                    # Last resort: try gemini-pro
                    print(f"Warning: gemini-1.5-flash not available, trying gemini-pro...")
                    try:
                        self.model = genai.GenerativeModel("gemini-pro")
                        self.model_name = "gemini-pro"
                    except Exception as e2:
                        raise ValueError(f"Failed to initialize Gemini model. Tried: {api_model_name}, gemini-2.0-flash-exp, gemini-1.5-flash, gemini-pro. Error: {e2}")
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.dependency_graph_builder = dependency_graph_builder or DependencyGraphBuilder(
            code_analyzer=self.code_analyzer
        )

    def generate_architecture_summary(
        self,
        code_structure: Dict[str, Any],
        dependency_graph: Dict[str, Any],
        complexity_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate architecture summary using LLM.

        Args:
            code_structure: Summary of code structure (from code_analyzer)
            dependency_graph: Dependency graph data (from dependency_graph_builder)
            complexity_metrics: Complexity metrics aggregated across files

        Returns:
            Dictionary with architecture analysis results
        """
        # Build prompt
        prompt = self._build_architecture_prompt(
            code_structure, dependency_graph, complexity_metrics
        )

        # Call LLM with structured output
        response = self._call_llm_with_structure(
            prompt, ArchitectureSummary, "architecture_analysis"
        )

        return response

    def _build_architecture_prompt(
        self,
        code_structure: Dict[str, Any],
        dependency_graph: Dict[str, Any],
        complexity_metrics: Dict[str, Any],
    ) -> str:
        """
        Build prompt for architecture analysis.

        Args:
            code_structure: Code structure summary
            dependency_graph: Dependency graph data
            complexity_metrics: Complexity metrics

        Returns:
            Formatted prompt string
        """
        prompt = """You are a senior software architect analyzing a Python codebase.

Analyze the provided code structure, dependency graph, and complexity metrics to provide a comprehensive architecture summary.

## Code Structure Summary:
{code_structure}

## Dependency Graph:
{dependency_graph}

## Complexity Metrics:
{complexity_metrics}

## Your Task:
Analyze this codebase and provide a structured assessment covering:
1. **Architecture Type**: Identify the architectural pattern (Layered, MVC, Microservices, Monolithic, Service-Oriented, etc.)
2. **Key Modules**: List the most important modules that form the core of the system
3. **Data Flow**: Describe how data flows through the system, including entry points, processing layers, and data storage
4. **Risks**: Identify architectural risks with severity levels (high/medium/low) and descriptions
5. **Strengths**: List architectural strengths and good practices observed
6. **Recommendations**: Provide high-level recommendations for improvement

Return your analysis as a JSON object with the following structure:
{{
    "architecture_type": "string",
    "key_modules": ["module1", "module2", ...],
    "data_flow": "description of data flow",
    "risks": [
        {{"severity": "high|medium|low", "description": "risk description"}},
        ...
    ],
    "strengths": ["strength1", "strength2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...]
}}

Be specific, actionable, and focus on architectural concerns rather than code-level details.
"""

        # Format the prompt with actual data
        formatted_prompt = prompt.format(
            code_structure=json.dumps(code_structure, indent=2),
            dependency_graph=json.dumps(dependency_graph, indent=2),
            complexity_metrics=json.dumps(complexity_metrics, indent=2),
        )

        return formatted_prompt

    def _call_llm_with_structure(
        self,
        prompt: str,
        response_model: BaseModel,
        task_name: str = "analysis",
    ) -> Dict[str, Any]:
        """
        Call LLM with structured output requirement.

        Args:
            prompt: Prompt to send to LLM
            response_model: Pydantic model for structured output
            task_name: Name of the task (for error messages)

        Returns:
            Parsed and validated response as dictionary
        """
        try:
            # Use Gemini API with JSON mode
            full_prompt = f"""You are a senior software architect. Always respond with valid JSON only.

{prompt}

IMPORTANT: Respond ONLY with valid JSON. Do not include any markdown formatting, code blocks, or explanatory text. Just the JSON object."""
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,  # Lower temperature for more consistent analysis
                response_mime_type="application/json",
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            # Extract response content
            content = response.text

            # Parse JSON
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError as e:
                # Try to extract JSON from markdown code blocks
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_data = json.loads(content[json_start:json_end].strip())
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    json_data = json.loads(content[json_start:json_end].strip())
                else:
                    raise ValueError(f"Failed to parse JSON from LLM response: {e}")

            # Validate with Pydantic model
            validated = response_model(**json_data)

            return validated.model_dump()

        except ValidationError as e:
            raise ValueError(
                f"LLM response validation failed for {task_name}: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"LLM call failed for {task_name}: {str(e)}")

    def analyze_codebase_architecture(
        self,
        file_analyses: List[Dict[str, Any]],
        dependency_graph_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Complete workflow: analyze codebase and generate architecture summary.

        Args:
            file_analyses: List of file analysis results from code_analyzer
            dependency_graph_data: Dependency graph JSON from dependency_graph_builder

        Returns:
            Complete architecture analysis
        """
        # Aggregate code structure
        code_structure = self._aggregate_code_structure(file_analyses)

        # Aggregate complexity metrics
        complexity_metrics = self._aggregate_complexity_metrics(file_analyses)

        # Generate architecture summary
        summary = self.generate_architecture_summary(
            code_structure, dependency_graph_data, complexity_metrics
        )

        return {
            "architecture_summary": summary,
            "code_structure": code_structure,
            "complexity_metrics": complexity_metrics,
            "dependency_graph_stats": dependency_graph_data.get("statistics", {}),
        }

    def _aggregate_code_structure(
        self, file_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate code structure from multiple file analyses.

        Args:
            file_analyses: List of file analysis results

        Returns:
            Aggregated code structure summary
        """
        total_files = len(file_analyses)
        total_classes = 0
        total_functions = 0
        total_imports = 0
        all_classes = []
        all_functions = []
        file_summaries = []

        for analysis in file_analyses:
            if "error" in analysis:
                continue

            file_name = analysis.get("file_name", "unknown")
            classes = analysis.get("classes", [])
            functions = analysis.get("functions", [])
            imports = analysis.get("imports", [])

            total_classes += len(classes)
            total_functions += len(functions)
            total_imports += len(imports)

            all_classes.extend([c["name"] for c in classes])
            all_functions.extend([f["name"] for f in functions])

            file_summaries.append({
                "file": file_name,
                "classes": len(classes),
                "functions": len(functions),
                "imports": len(imports),
            })

        return {
            "total_files": total_files,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "total_imports": total_imports,
            "class_names": all_classes[:20],  # Limit for prompt size
            "function_names": all_functions[:20],
            "file_summaries": file_summaries[:50],  # Limit for prompt size
        }

    def _aggregate_complexity_metrics(
        self, file_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate complexity metrics from multiple file analyses.

        Args:
            file_analyses: List of file analysis results

        Returns:
            Aggregated complexity metrics
        """
        all_complexities = []
        maintainability_indices = []
        total_loc = 0
        total_sloc = 0

        for analysis in file_analyses:
            if "error" in analysis:
                continue

            complexity = analysis.get("complexity", {})
            metrics = analysis.get("metrics", {})

            # Collect function complexities
            if "cyclomatic_complexity" in complexity:
                for item in complexity["cyclomatic_complexity"]:
                    all_complexities.append(item.get("complexity", 0))

            # Collect maintainability indices
            if "maintainability_index" in complexity:
                mi = complexity["maintainability_index"]
                if isinstance(mi, (int, float)):
                    maintainability_indices.append(mi)
                elif isinstance(mi, dict) and "average" in mi:
                    maintainability_indices.append(mi["average"])

            # Aggregate code metrics
            if isinstance(metrics, dict):
                total_loc += metrics.get("loc", 0)
                total_sloc += metrics.get("sloc", 0)

        avg_complexity = (
            sum(all_complexities) / len(all_complexities) if all_complexities else 0
        )
        max_complexity = max(all_complexities) if all_complexities else 0
        avg_maintainability = (
            sum(maintainability_indices) / len(maintainability_indices)
            if maintainability_indices
            else 0
        )

        return {
            "average_complexity": round(avg_complexity, 2),
            "max_complexity": max_complexity,
            "average_maintainability_index": round(avg_maintainability, 2),
            "total_lines_of_code": total_loc,
            "total_source_lines": total_sloc,
            "complexity_distribution": {
                "low": len([c for c in all_complexities if c <= 5]),
                "medium": len([c for c in all_complexities if 5 < c <= 10]),
                "high": len([c for c in all_complexities if c > 10]),
            },
        }

    def analyze_general_repository(
        self,
        repo_structure: Dict[str, Any],
        repo_path: str,
    ) -> Dict[str, Any]:
        """
        Analyze a repository without Python files using LLM.

        Args:
            repo_structure: Repository structure information
            repo_path: Path to the repository

        Returns:
            Architecture analysis dictionary
        """
        if not self.model:
            raise ValueError("LLM model not available")

        # Build prompt for general analysis
        prompt = f"""You are a senior software architect analyzing a codebase.

## Repository Structure:
- Languages detected: {', '.join(repo_structure.get('languages', ['Unknown']))}
- Total files: {repo_structure.get('total_files', 0)}
- Code files: {len(repo_structure.get('code_files', []))}
- File types: {json.dumps(repo_structure.get('file_types', {}), indent=2)}

## Your Task:
Analyze this repository and provide a structured assessment covering:
1. **Architecture Type**: Identify the architectural pattern
2. **Key Modules**: List important modules/directories
3. **Data Flow**: Describe how data flows through the system
4. **Risks**: Identify architectural risks with severity levels
5. **Strengths**: List architectural strengths
6. **Recommendations**: Provide high-level recommendations

Return your analysis as a JSON object with the following structure:
{{
    "architecture_type": "string",
    "key_modules": ["module1", "module2", ...],
    "data_flow": "description of data flow",
    "risks": [
        {{"severity": "high|medium|low", "description": "risk description"}},
        ...
    ],
    "strengths": ["strength1", "strength2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...]
}}
"""

        try:
            # Use Gemini API with JSON mode
            full_prompt = f"""You are a senior software architect. Always respond with valid JSON only.

{prompt}

IMPORTANT: Respond ONLY with valid JSON. Do not include any markdown formatting, code blocks, or explanatory text. Just the JSON object."""
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json",
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            content = response.text
            json_data = json.loads(content)

            # Wrap in same structure as Python analysis
            return {
                "architecture_summary": json_data,
                "code_structure": {
                    "total_files": repo_structure.get("total_files", 0),
                    "languages": repo_structure.get("languages", []),
                    "file_types": repo_structure.get("file_types", {}),
                },
                "complexity_metrics": {},
                "dependency_graph_stats": {},
            }

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            # Check if it's an API key error
            if "api key" in error_msg.lower() or "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                raise ValueError(f"Gemini API authentication failed: {error_msg}")
            raise RuntimeError(f"General repository analysis failed: {error_msg}")

    def ask_question(
        self,
        question: str,
        relevant_chunks: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Answer a question about the codebase using RAG.

        Args:
            question: User's question
            relevant_chunks: Relevant code chunks from vector store search
            context: Optional additional context (architecture summary, etc.)

        Returns:
            LLM-generated answer
        """
        # Build context from chunks
        chunk_context = "\n\n".join(
            [
                f"File: {chunk['metadata'].get('file_name', 'unknown')}\n"
                f"Type: {chunk['metadata'].get('chunk_type', 'unknown')}\n"
                f"Content:\n{chunk['content']}"
                for chunk in relevant_chunks[:5]  # Limit to top 5 chunks
            ]
        )

        prompt = f"""You are a codebase expert answering questions about a Python codebase.

## Question:
{question}

## Relevant Code Context:
{chunk_context}
"""

        if context:
            prompt += f"\n## Additional Context:\n{json.dumps(context, indent=2)}"

        prompt += "\n\nProvide a clear, accurate answer based on the code context provided."

        try:
            full_prompt = f"""You are a helpful codebase expert. Answer questions accurately based on the provided code context.

{prompt}"""
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            return response.text

        except Exception as e:
            raise RuntimeError(f"Failed to generate answer: {str(e)}")
    
    def ask_question_without_rag(
        self,
        question: str,
        repo_name: Optional[str] = None,
    ) -> str:
        """
        Answer a question about a codebase without RAG context.
        Used when vector store is not available (e.g., for non-Python repos).
        
        Args:
            question: The question to answer
            repo_name: Optional repository name for context
            
        Returns:
            Answer string
        """
        if not self.model:
            raise ValueError("LLM model not available")
        
        context = f"Repository: {repo_name}\n" if repo_name else ""
        
        prompt = f"""You are a helpful code assistant. Answer the following question about a codebase.

{context}Question: {question}

Please provide a helpful answer based on general software engineering knowledge and best practices. 
If the question is specific to code that would require code context, mention that detailed code analysis 
would be helpful but provide the best answer you can with the information available.

Answer:"""
        
        try:
            response = self.model.generate_content(prompt)
            answer_text = response.text.strip()
            return answer_text
        except Exception as e:
            error_msg = f"Failed to generate answer: {str(e)}"
            print(f"LLM error: {error_msg}")
            raise ValueError(error_msg)

    def detect_code_smells_general(
        self,
        repo_structure: Dict[str, Any],
        repo_path: str,
        architecture_summary: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Detect code smells in a non-Python repository using LLM.

        Args:
            repo_structure: Repository structure information
            repo_path: Path to the repository
            architecture_summary: Architecture analysis results

        Returns:
            List of code smell dictionaries
        """
        if not self.model:
            raise ValueError("LLM model not available")

        # Build prompt for code smell detection
        prompt = f"""You are a code quality expert analyzing a codebase for code smells and issues.

## Repository Information:
- Languages: {', '.join(repo_structure.get('languages', ['Unknown']))}
- Total files: {repo_structure.get('total_files', 0)}
- Code files: {len(repo_structure.get('code_files', []))}
- Architecture: {architecture_summary.get('architecture_type', 'Unknown') if isinstance(architecture_summary, dict) else 'Unknown'}

## Your Task:
Analyze this repository and identify code smells, anti-patterns, and potential issues. 
Consider common issues like:
- Large files or functions
- Tight coupling
- Duplicated code
- Missing documentation
- Poor naming conventions
- Security vulnerabilities
- Performance issues
- Maintainability concerns

Return your analysis as a JSON array of code smells, each with:
{{
    "issue": "name of the issue",
    "severity": "high|medium|low",
    "description": "detailed description of the issue",
    "location": "file path, module name, or specific location where the issue is found (e.g., 'src/utils.js' or 'components/Button.tsx')",
    "impact": "description of how this issue impacts the codebase (e.g., 'Reduces maintainability', 'Increases bug risk', 'Makes testing difficult')",
    "suggestion": "how to fix or improve it (optional)"
}}

Return a JSON array like:
[
    {{"issue": "...", "severity": "...", "description": "...", "location": "...", "impact": "...", "suggestion": "..."}},
    ...
]
"""

        try:
            full_prompt = f"""You are a code quality expert. Always respond with valid JSON only.

{prompt}

IMPORTANT: Respond ONLY with a valid JSON array. Do not include any markdown formatting, code blocks, or explanatory text. Just the JSON array."""
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json",
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            content = response.text
            json_data = json.loads(content)
            
            # Ensure it's a list
            if not isinstance(json_data, list):
                json_data = [json_data] if json_data else []
            
            # Format to match expected structure
            code_smells = []
            for item in json_data:
                # Map file_path to location if location is not provided
                location = item.get("location") or item.get("file_path", "Unknown location")
                # Ensure impact is provided, use recommendation as fallback if needed
                impact = item.get("impact") or item.get("recommendation", "Impact not specified")
                
                code_smells.append({
                    "issue": item.get("issue", "Unknown issue"),
                    "severity": item.get("severity", "medium"),
                    "description": item.get("description", ""),
                    "location": location,
                    "impact": impact,
                    "suggestion": item.get("suggestion") or item.get("recommendation", ""),
                })
            
            return code_smells

        except json.JSONDecodeError as e:
            print(f"⚠ Failed to parse code smells JSON: {e}")
            return []
        except Exception as e:
            error_msg = str(e)
            print(f"⚠ Code smell detection failed: {error_msg}")
            return []

    def generate_project_description(
        self,
        repo_structure: Dict[str, Any],
        repo_path: str,
        architecture_summary: Dict[str, Any],
    ) -> str:
        """
        Generate a project description using LLM.

        Args:
            repo_structure: Repository structure information
            repo_path: Path to the repository
            architecture_summary: Architecture analysis results

        Returns:
            Project description string
        """
        if not self.model:
            raise ValueError("LLM model not available")

        # Extract architecture type
        arch_type = "Unknown"
        if isinstance(architecture_summary, dict):
            if "architecture_type" in architecture_summary:
                arch_type = architecture_summary["architecture_type"]
            elif "architecture_summary" in architecture_summary:
                arch_summary = architecture_summary.get("architecture_summary", {})
                if isinstance(arch_summary, dict):
                    arch_type = arch_summary.get("architecture_type", "Unknown")

        # Extract key module names from code_files (which are dicts with 'path' key)
        code_files = repo_structure.get('code_files', [])
        key_modules = []
        if code_files:
            # Extract file paths/names from the dictionaries
            for file_info in code_files[:10]:
                if isinstance(file_info, dict):
                    # Use the 'path' or 'name' field if available
                    module_name = file_info.get('path') or file_info.get('name', '')
                    if module_name:
                        key_modules.append(module_name)
                elif isinstance(file_info, str):
                    key_modules.append(file_info)
        
        key_modules_str = ', '.join(key_modules) if key_modules else 'None detected'

        # Build prompt
        prompt = f"""You are a technical writer creating a project description.

## Repository Information:
- Languages: {', '.join(repo_structure.get('languages', ['Unknown']))}
- Total files: {repo_structure.get('total_files', 0)}
- Architecture: {arch_type}
- Key modules: {key_modules_str}

## Your Task:
Write a concise, informative project description (2-4 sentences) that:
1. Identifies what type of project this is
2. Describes its main purpose or functionality
3. Mentions key technologies or frameworks used
4. Highlights the architectural approach if notable

Be specific and informative. Write in third person.

Example format:
"This is a [type] application built with [technologies]. It follows a [architecture] architecture pattern and provides [main functionality]. The project uses [key technologies/frameworks] for [purpose]."

Project Description:"""

        try:
            response = self.model.generate_content(prompt)
            description = response.text.strip()
            
            # Clean up any markdown formatting
            if description.startswith('"') and description.endswith('"'):
                description = description[1:-1]
            if description.startswith("'") and description.endswith("'"):
                description = description[1:-1]
            
            return description

        except Exception as e:
            error_msg = str(e)
            print(f"⚠ Project description generation failed: {error_msg}")
            return ""


# Example usage
if __name__ == "__main__":
    # Example: Generate architecture summary
    # reasoner = LLMReasoner(api_key="your-key")
    #
    # # Analyze files
    # file_analyses = [...]  # From code_analyzer
    # dependency_graph = {...}  # From dependency_graph_builder
    #
    # result = reasoner.analyze_codebase_architecture(file_analyses, dependency_graph)
    # print(json.dumps(result, indent=2))
    pass  # Placeholder for example code
