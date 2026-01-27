"""
Code Smell Detection Service

Combines AST metrics and LLM analysis to detect code smells and architectural issues.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from .code_analyzer import CodeAnalyzer
from .dependency_graph import DependencyGraphBuilder
from .llm_reasoner import LLMReasoner


class CodeSmell(BaseModel):
    """Structured model for a code smell/issue."""

    issue: str = Field(description="Name of the code smell or issue")
    severity: str = Field(description="Severity level: high, medium, or low")
    description: str = Field(description="Detailed description of the issue")
    location: str = Field(description="File or module where the issue is found")
    impact: str = Field(description="Impact of this issue on the codebase")
    suggestion: Optional[str] = Field(
        default=None, description="Suggestion for fixing the issue"
    )


class CodeSmellDetector:
    """Service for detecting code smells using metrics and LLM analysis."""

    def __init__(
        self,
        code_analyzer: Optional[CodeAnalyzer] = None,
        dependency_graph_builder: Optional[DependencyGraphBuilder] = None,
        llm_reasoner: Optional[LLMReasoner] = None,
    ):
        """
        Initialize the code smell detector.

        Args:
            code_analyzer: Optional CodeAnalyzer instance
            dependency_graph_builder: Optional DependencyGraphBuilder instance
            llm_reasoner: Optional LLMReasoner instance
        """
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.dependency_graph_builder = dependency_graph_builder or DependencyGraphBuilder(
            code_analyzer=self.code_analyzer
        )
        self.llm_reasoner = llm_reasoner

        self.thresholds = {
            "god_class_method_count": 15,
            "god_class_line_count": 500,
            "high_complexity": 10,
            "very_high_complexity": 20,
            "large_function_lines": 100,
            "many_parameters": 5,
        }

    def detect_code_smells(
        self,
        file_analyses: List[Dict[str, Any]],
        dependency_graph_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect code smells across the codebase.

        Args:
            file_analyses: List of file analysis results from code_analyzer
            dependency_graph_data: Optional dependency graph data

        Returns:
            List of detected code smells, prioritized by severity
        """
        all_smells = []

        metric_smells = self._detect_metric_based_smells(file_analyses)
        all_smells.extend(metric_smells)

        if dependency_graph_data:
            dependency_smells = self._detect_dependency_smells(
                file_analyses, dependency_graph_data
            )
            all_smells.extend(dependency_smells)

        if self.llm_reasoner:
            try:
                llm_smells = self._detect_llm_based_smells(file_analyses)
                all_smells.extend(llm_smells)
            except Exception as e:
                print(f"LLM-based detection failed: {e}")

        return self._prioritize_smells(all_smells)

    def _detect_metric_based_smells(
        self, file_analyses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect code smells using AST metrics.

        Args:
            file_analyses: List of file analysis results

        Returns:
            List of detected code smells
        """
        smells = []

        for analysis in file_analyses:
            if "error" in analysis:
                continue

            file_path = analysis.get("file_path", "unknown")
            file_name = analysis.get("file_name", "unknown")
            
            relative_path = self._get_relative_path_display(file_path, file_name)

            for cls in analysis.get("classes", []):
                god_class_smells = self._detect_god_class(cls, relative_path, file_name)
                smells.extend(god_class_smells)

            if analysis.get("language") == "python" and analysis.get("complexity"):
                for func in analysis.get("functions", []):
                    complexity_smells = self._detect_high_complexity(
                        func, analysis.get("complexity", {}), relative_path, file_name
                    )
                    smells.extend(complexity_smells)

            docstring_smells = self._detect_missing_docstrings(
                analysis, relative_path, file_name
            )
            smells.extend(docstring_smells)

            large_function_smells = self._detect_large_functions(
                analysis, relative_path, file_name
            )
            smells.extend(large_function_smells)

        return smells

    def _get_relative_path_display(self, file_path: str, file_name: str) -> str:
        if not file_path or file_path == "unknown":
            return file_name
        
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            return str(path_obj).replace("\\", "/")
        
        path_str = str(path_obj).replace("\\", "/")
        
        repo_indicators = [
            "repos/", "backend/", "frontend/", "src/", "app/", "lib/", 
            "components/", "services/", "utils/", "models/", "controllers/",
            "routes/", "routers/", "pages/", "hooks/", "helpers/"
        ]
        for indicator in repo_indicators:
            if indicator in path_str:
                parts = path_str.split(indicator, 1)
                if len(parts) > 1:
                    return indicator + parts[1]
        
        parts = path_obj.parts
        if len(parts) >= 3:
            return "/".join(parts[-3:])
        elif len(parts) >= 2:
            return "/".join(parts[-2:])
        elif len(parts) == 1:
            return parts[0]
        
        return file_name

    def _detect_god_class(
        self, cls: Dict[str, Any], file_path: str, file_name: str
    ) -> List[Dict[str, Any]]:
        """
        Detect God Class anti-pattern.

        Args:
            cls: Class information from analysis
            file_path: Path to the file
            file_name: Name of the file

        Returns:
            List of detected god class smells
        """
        smells = []
        method_count = len(cls.get("methods", []))
        attribute_count = len(cls.get("attributes", []))

        if method_count > self.thresholds["god_class_method_count"]:
            smells.append({
                "issue": "God Class",
                "severity": "high" if method_count > 25 else "medium",
                "description": f"Class '{cls['name']}' has {method_count} methods, indicating too many responsibilities. God classes violate Single Responsibility Principle.",
                "location": f"{file_path}::{cls['name']}",
                "impact": "High maintenance cost, difficult to test, tight coupling",
                "suggestion": f"Consider splitting '{cls['name']}' into smaller, focused classes. Extract related methods into separate classes.",
            })

        if "end_line" in cls and "line_number" in cls:
            line_count = cls["end_line"] - cls["line_number"]
            if line_count > self.thresholds["god_class_line_count"]:
                smells.append({
                    "issue": "God Class (Large)",
                    "severity": "high" if line_count > 1000 else "medium",
                    "description": f"Class '{cls['name']}' is {line_count} lines long, indicating excessive complexity.",
                    "location": f"{file_path}::{cls['name']}",
                    "impact": "Difficult to understand and maintain",
                    "suggestion": "Break down into smaller classes with single responsibilities",
                })

        return smells

    def _detect_high_complexity(
        self,
        func: Dict[str, Any],
        complexity_data: Dict[str, Any],
        file_path: str,
        file_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Detect functions with high cyclomatic complexity.

        Args:
            func: Function information
            complexity_data: Complexity metrics for the file
            file_path: Path to the file
            file_name: Name of the file

        Returns:
            List of detected complexity smells
        """
        smells = []

        func_complexity = None
        if "cyclomatic_complexity" in complexity_data:
            for item in complexity_data["cyclomatic_complexity"]:
                if item.get("name") == func["name"]:
                    func_complexity = item.get("complexity", 0)
                    break

        if func_complexity:
            if func_complexity > self.thresholds["very_high_complexity"]:
                severity = "high"
            elif func_complexity > self.thresholds["high_complexity"]:
                severity = "medium"
            else:
                return smells

            smells.append({
                "issue": "High Cyclomatic Complexity",
                "severity": severity,
                "description": f"Function '{func['name']}' has cyclomatic complexity of {func_complexity}. High complexity makes code difficult to understand and test.",
                "location": f"{file_path}::{func['name']}",
                "impact": "Increased bug risk, difficult to test, hard to maintain",
                "suggestion": f"Refactor '{func['name']}' to reduce complexity. Consider extracting helper functions or using early returns.",
            })

        param_count = func.get("parameter_count", 0)
        if param_count > self.thresholds["many_parameters"]:
            smells.append({
                "issue": "Too Many Parameters",
                "severity": "medium",
                "description": f"Function '{func['name']}' has {param_count} parameters. Functions with many parameters are hard to use and maintain.",
                "location": f"{file_path}::{func['name']}",
                "impact": "Difficult to call correctly, indicates missing abstraction",
                "suggestion": "Consider grouping related parameters into a data class or configuration object",
            })

        return smells

    def _detect_missing_docstrings(
        self, analysis: Dict[str, Any], file_path: str, file_name: str
    ) -> List[Dict[str, Any]]:
        """
        Detect missing docstrings.

        Args:
            analysis: File analysis results
            file_path: Path to the file
            file_name: Name of the file

        Returns:
            List of missing docstring smells
        """
        smells = []

        for cls in analysis.get("classes", []):
            if not cls.get("docstring"):
                smells.append({
                    "issue": "Missing Docstring",
                    "severity": "low",
                    "description": f"Class '{cls['name']}' is missing a docstring.",
                    "location": f"{file_path}::{cls['name']}",
                    "impact": "Reduced code readability and maintainability",
                    "suggestion": "Add a docstring explaining the class's purpose and responsibilities",
                })

        for func in analysis.get("functions", []):
            if func["name"].startswith("_"):
                continue

            if not func.get("docstring"):
                smells.append({
                    "issue": "Missing Docstring",
                    "severity": "low",
                    "description": f"Public function '{func['name']}' is missing a docstring.",
                    "location": f"{file_path}::{func['name']}",
                    "impact": "Reduced code readability and API documentation",
                    "suggestion": "Add a docstring explaining the function's purpose, parameters, and return value",
                })

        return smells

    def _detect_large_functions(
        self, analysis: Dict[str, Any], file_path: str, file_name: str
    ) -> List[Dict[str, Any]]:
        """
        Detect functions that are too large.

        Args:
            analysis: File analysis results
            file_path: Path to the file
            file_name: Name of the file

        Returns:
            List of large function smells
        """
        smells = []

        for func in analysis.get("functions", []):
            if "end_line" in func and "line_number" in func:
                line_count = func["end_line"] - func["line_number"]
                if line_count > self.thresholds["large_function_lines"]:
                    smells.append({
                        "issue": "Large Function",
                        "severity": "medium" if line_count > 200 else "low",
                        "description": f"Function '{func['name']}' is {line_count} lines long. Large functions are hard to understand and maintain.",
                        "location": f"{file_path}::{func['name']}",
                        "impact": "Difficult to test and maintain",
                        "suggestion": "Break down into smaller, focused functions",
                    })

        return smells

    def _detect_dependency_smells(
        self,
        file_analyses: List[Dict[str, Any]],
        dependency_graph_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Detect dependency-related code smells.

        Args:
            file_analyses: List of file analysis results
            dependency_graph_data: Dependency graph data

        Returns:
            List of dependency-related smells
        """
        smells = []

        cycles = dependency_graph_data.get("cycles", [])
        if cycles:
            for cycle in cycles:
                cycle_files_display = []
                cycle_files_names = []
                for f in cycle:
                    path_obj = Path(f)
                    cycle_files_names.append(path_obj.name)
                    if path_obj.is_absolute():
                        parts = path_obj.parts
                        if len(parts) >= 2:
                            path_str = str(path_obj)
                            repo_indicators = ["repos/", "backend/", "frontend/", "src/", "app/", "lib/", "components/"]
                            found = False
                            for indicator in repo_indicators:
                                if indicator in path_str:
                                    parts = path_str.split(indicator, 1)
                                    if len(parts) > 1:
                                        cycle_files_display.append(indicator + parts[1].replace("\\", "/"))
                                        found = True
                                        break
                            if not found:
                                cycle_files_display.append("/".join(parts[-3:]))
                        else:
                            cycle_files_display.append(path_obj.name)
                    else:
                        cycle_files_display.append(str(path_obj).replace("\\", "/"))
                
                smells.append({
                    "issue": "Circular Dependency",
                    "severity": "high",
                    "description": f"Circular dependency detected: {' -> '.join(cycle_files_names)} -> {cycle_files_names[0]}",
                    "location": " -> ".join(cycle_files_display),
                    "impact": "Creates tight coupling, makes code difficult to test and maintain",
                    "suggestion": "Break the cycle by introducing an abstraction layer or dependency inversion",
                })

        edges = dependency_graph_data.get("edges", [])
        node_dependencies = {}
        for edge in edges:
            source = edge.get("source", "")
            if source not in node_dependencies:
                node_dependencies[source] = 0
            node_dependencies[source] += 1

        for file_path, dep_count in node_dependencies.items():
            if dep_count > 10:
                path_obj = Path(file_path)
                file_name = path_obj.name
                
                if path_obj.is_absolute():
                    parts = path_obj.parts
                    if len(parts) >= 2:
                        path_str = str(path_obj)
                        repo_indicators = ["repos/", "backend/", "frontend/", "src/", "app/", "lib/", "components/"]
                        location = file_name
                        for indicator in repo_indicators:
                            if indicator in path_str:
                                parts = path_str.split(indicator, 1)
                                if len(parts) > 1:
                                    location = indicator + parts[1].replace("\\", "/")
                                    break
                        if location == file_name:
                            location = "/".join(parts[-3:])
                    else:
                        location = file_name
                else:
                    location = str(path_obj).replace("\\", "/")
                
                smells.append({
                    "issue": "Tight Coupling",
                    "severity": "medium",
                    "description": f"File '{file_name}' depends on {dep_count} other files, indicating tight coupling.",
                    "location": location,
                    "impact": "Changes in dependencies affect this file, difficult to test in isolation",
                    "suggestion": "Consider introducing interfaces or dependency injection to reduce coupling",
                })

        return smells

    def _detect_llm_based_smells(
        self, file_analyses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to detect nuanced code smells.

        Args:
            file_analyses: List of file analysis results

        Returns:
            List of LLM-detected code smells
        """
        if not self.llm_reasoner:
            return []

        context = {
            "files": [
                {
                    "file": analysis.get("file_name", "unknown"),
                    "classes": [
                        {
                            "name": cls["name"],
                            "methods": len(cls.get("methods", [])),
                            "has_docstring": bool(cls.get("docstring")),
                        }
                        for cls in analysis.get("classes", [])
                    ],
                    "functions": [
                        {
                            "name": func["name"],
                            "parameters": func.get("parameter_count", 0),
                            "has_docstring": bool(func.get("docstring")),
                        }
                        for func in analysis.get("functions", [])
                    ],
                }
                for analysis in file_analyses[:20]
            ]
        }

        prompt = f"""You are a code quality expert analyzing a Python codebase for code smells.

## Code Structure:
{json.dumps(context, indent=2)}

## Your Task:
Identify code smells and anti-patterns that may not be caught by static metrics alone. Look for:
- Design pattern violations
- Naming issues
- Code duplication patterns
- Architectural issues
- Best practice violations

Return a JSON array of code smells, each with:
- "issue": name of the issue
- "severity": "high", "medium", or "low"
- "description": detailed description
- "location": file or module name
- "impact": impact on codebase
- "suggestion": how to fix

Return only valid JSON array, no markdown.
"""

        try:
            response = self.llm_reasoner.client.chat.completions.create(
                model=self.llm_reasoner.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a code quality expert. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            content = response.choices[0].message.content
            json_data = json.loads(content)

            if isinstance(json_data, dict):
                for key in ["smells", "issues", "code_smells", "results"]:
                    if key in json_data and isinstance(json_data[key], list):
                        smells = json_data[key]
                        break
                else:
                    smells = list(json_data.values()) if json_data else []
            else:
                smells = json_data if isinstance(json_data, list) else []

            validated_smells = []
            for smell in smells:
                try:
                    smell.setdefault("location", smell.get("file_path", "Unknown location"))
                    smell.setdefault("impact", smell.get("recommendation", "Impact not specified"))
                    if not smell.get("location") or smell["location"] == "":
                        smell["location"] = "Unknown location"
                    if not smell.get("impact") or smell["impact"] == "":
                        smell["impact"] = "Impact not specified"
                    
                    validated = CodeSmell(**smell)
                    validated_smells.append(validated.model_dump())
                except Exception as e:
                    print(f"⚠ Skipping invalid code smell entry: {e}")
                    continue

            return validated_smells

        except Exception as e:
            print(f"LLM-based smell detection failed: {e}")
            return []

    def _prioritize_smells(self, smells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize code smells by severity and ensure all required fields are present.

        Args:
            smells: List of detected code smells

        Returns:
            Prioritized list (high -> medium -> low) with all required fields
        """
        for smell in smells:
            if not smell.get("location") or smell["location"] == "":
                smell["location"] = (
                    smell.get("file_path") or 
                    smell.get("file_name") or 
                    "Unknown location"
                )
            
            if not smell.get("impact") or smell["impact"] == "":
                smell["impact"] = (
                    smell.get("recommendation") or 
                    "Impact not specified"
                )
        
        severity_order = {"high": 0, "medium": 1, "low": 2}

        def sort_key(smell):
            severity = smell.get("severity", "low").lower()
            return (severity_order.get(severity, 2), smell.get("issue", ""))

        return sorted(smells, key=sort_key)

    def get_smell_summary(self, smells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics of detected code smells.

        Args:
            smells: List of code smells

        Returns:
            Summary dictionary
        """
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        issue_types = {}

        for smell in smells:
            severity = smell.get("severity", "low").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            issue = smell.get("issue", "Unknown")
            issue_types[issue] = issue_types.get(issue, 0) + 1

        return {
            "total_smells": len(smells),
            "by_severity": severity_counts,
            "by_issue_type": issue_types,
        }


