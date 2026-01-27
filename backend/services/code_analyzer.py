"""
Static Code Analysis Service using AST and Multi-Language Support

Analyzes code files to extract classes, functions, imports, and complexity metrics.
Supports Python (AST), JavaScript/TypeScript, Java, C#, Go, and other languages (regex-based).
"""

import ast
import inspect
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze


class CodeAnalyzer:
    """Service for static code analysis using AST parsing (Python) and regex patterns (other languages)."""

    def __init__(self):
        """Initialize the code analyzer."""
        self.language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cs": "csharp",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
        }

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        return self.language_map.get(ext, "unknown")

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a code file and extract structured information.
        Supports Python (AST) and other languages (regex-based).

        Args:
            file_path: Path to the code file

        Returns:
            Dictionary containing:
            {
                "file_path": "...",
                "file_name": "...",
                "language": "...",
                "classes": [...],
                "functions": [...],
                "imports": [...],
                "module_variables": [...],
                "complexity": {...},
                "metrics": {...},
                "errors": [...]
            }
        """
        file_path_obj = Path(file_path)
        language = self._detect_language(file_path)
        
        if not file_path_obj.exists():
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "language": language,
                "classes": [],
                "functions": [],
                "imports": [],
                "module_variables": [],
                "error": f"File does not exist: {file_path}",
            }

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source_code = f.read()
        except Exception as e:
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "language": language,
                "classes": [],
                "functions": [],
                "imports": [],
                "module_variables": [],
                "error": f"Failed to read file: {str(e)}",
            }

        if language == "python":
            return self._analyze_python_file(file_path, file_path_obj, source_code)
        else:
            return self._analyze_non_python_file(file_path, file_path_obj, source_code, language)

    def _analyze_python_file(self, file_path: str, file_path_obj: Path, source_code: str) -> Dict[str, Any]:
        """Analyze Python file using AST."""
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "language": "python",
                "classes": [],
                "functions": [],
                "imports": [],
                "module_variables": [],
                "error": f"Syntax error: {str(e)}",
                "syntax_error_line": e.lineno,
            }
        except Exception as e:
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "language": "python",
                "classes": [],
                "functions": [],
                "imports": [],
                "module_variables": [],
                "error": f"Failed to parse AST: {str(e)}",
            }

        classes = self._extract_classes(tree, source_code)
        functions = self._extract_functions(tree, source_code)
        imports = self._extract_imports(tree)
        module_variables = self._extract_module_variables(tree, source_code)

        complexity_metrics = self._calculate_complexity(source_code, file_path)
        code_metrics = self._calculate_code_metrics(source_code)

        return {
            "file_path": str(file_path),
            "file_name": file_path_obj.name,
            "language": "python",
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "module_variables": module_variables,
            "complexity": complexity_metrics,
            "metrics": code_metrics,
            "line_count": len(source_code.splitlines()),
        }

    def _analyze_non_python_file(self, file_path: str, file_path_obj: Path, source_code: str, language: str) -> Dict[str, Any]:
        """Analyze non-Python file using regex patterns."""
        lines = source_code.splitlines()
        
        classes = self._extract_classes_regex(source_code, language, lines)
        
        functions = self._extract_functions_regex(source_code, language, lines)
        
        imports = self._extract_imports_regex(source_code, language, lines)
        
        code_metrics = {
            "lines_of_code": len([l for l in lines if l.strip() and not l.strip().startswith("//")]),
            "total_lines": len(lines),
        }

        return {
            "file_path": str(file_path),
            "file_name": file_path_obj.name,
            "language": language,
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "module_variables": [],
            "complexity": {},
            "metrics": code_metrics,
            "line_count": len(lines),
        }

    def _extract_classes(self, tree: ast.AST, source_code: str) -> List[Dict[str, Any]]:
        """
        Extract all classes from the AST.

        Args:
            tree: Parsed AST tree
            source_code: Original source code for extracting docstrings

        Returns:
            List of class information dictionaries
        """
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "line_number": node.lineno,
                    "end_line": node.end_lineno if hasattr(node, "end_lineno") else None,
                    "docstring": ast.get_docstring(node),
                    "bases": [self._get_node_name(base) for base in node.bases],
                    "decorators": [self._get_decorator_name(dec) for dec in node.decorator_list],
                    "methods": [],
                    "attributes": [],
                }

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = self._extract_function_info(item, source_code)
                        class_info["methods"].append(method_info)

                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                class_info["attributes"].append({
                                    "name": target.id,
                                    "line_number": item.lineno,
                                })

                classes.append(class_info)

        return classes

    def _extract_functions(self, tree: ast.AST, source_code: str) -> List[Dict[str, Any]]:
        """
        Extract all module-level functions from the AST.

        Args:
            tree: Parsed AST tree
            source_code: Original source code for extracting docstrings

        Returns:
            List of function information dictionaries
        """
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                is_method = False
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        for item in parent.body:
                            if item == node:
                                is_method = True
                                break
                    if is_method:
                        break

                if not is_method:
                    func_info = self._extract_function_info(node, source_code)
                    functions.append(func_info)

        return functions

    def _extract_function_info(
        self, node: ast.FunctionDef, source_code: str
    ) -> Dict[str, Any]:
        """
        Extract detailed information about a function.

        Args:
            node: FunctionDef AST node
            source_code: Original source code

        Returns:
            Function information dictionary
        """
        parameters = []
        for arg in node.args.args:
            param_info = {
                "name": arg.arg,
                "annotation": self._get_node_name(arg.annotation) if arg.annotation else None,
            }
            parameters.append(param_info)

        return_annotation = None
        if node.returns:
            return_annotation = self._get_node_name(node.returns)

        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]

        statement_count = len([n for n in ast.walk(node) if isinstance(n, (ast.Expr, ast.Assign, ast.Return, ast.If, ast.For, ast.While))])

        return {
            "name": node.name,
            "line_number": node.lineno,
            "end_line": node.end_lineno if hasattr(node, "end_lineno") else None,
            "docstring": ast.get_docstring(node),
            "parameters": parameters,
            "parameter_count": len(parameters),
            "return_annotation": return_annotation,
            "decorators": decorators,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "statement_count": statement_count,
        }

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """
        Extract all import statements.

        Args:
            tree: Parsed AST tree

        Returns:
            List of import information dictionaries
        """
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line_number": node.lineno,
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line_number": node.lineno,
                    })

        return imports

    def _extract_module_variables(
        self, tree: ast.AST, source_code: str
    ) -> List[Dict[str, Any]]:
        """
        Extract module-level variables.

        Args:
            tree: Parsed AST tree
            source_code: Original source code

        Returns:
            List of module variable information dictionaries
        """
        module_variables = []
        top_level_nodes = [node for node in tree.body if isinstance(node, ast.Assign)]

        for node in top_level_nodes:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_info = {
                        "name": target.id,
                        "line_number": node.lineno,
                        "has_annotation": False,
                    }

                    if hasattr(node, "value"):
                        var_info["value_type"] = type(node.value).__name__

                    module_variables.append(var_info)

        return module_variables

    def _calculate_complexity(self, source_code: str, file_path: str) -> Dict[str, Any]:
        """
        Calculate cyclomatic complexity using radon.

        Args:
            source_code: Source code string
            file_path: Path to the file

        Returns:
            Complexity metrics dictionary
        """
        try:
            complexity_results = cc_visit(source_code)
            
            complexity_by_function = []
            for item in complexity_results:
                complexity_by_function.append({
                    "name": item.name,
                    "complexity": item.complexity,
                    "rank": item.rank,
                    "line_number": item.lineno,
                    "type": item.type,
                })

            maintainability_index = mi_visit(source_code, multi=True)

            return {
                "cyclomatic_complexity": complexity_by_function,
                "maintainability_index": maintainability_index,
                "average_complexity": (
                    sum(item.complexity for item in complexity_results) / len(complexity_results)
                    if complexity_results else 0
                ),
                "max_complexity": (
                    max(item.complexity for item in complexity_results)
                    if complexity_results else 0
                ),
            }
        except Exception as e:
            return {
                "error": f"Failed to calculate complexity: {str(e)}",
            }

    def _calculate_code_metrics(self, source_code: str) -> Dict[str, Any]:
        """
        Calculate basic code metrics using radon.

        Args:
            source_code: Source code string

        Returns:
            Code metrics dictionary
        """
        try:
            raw_metrics = analyze(source_code)
            
            return {
                "loc": raw_metrics.loc,
                "lloc": raw_metrics.lloc,
                "sloc": raw_metrics.sloc,
                "comments": raw_metrics.comments,
                "multi": raw_metrics.multi,
                "blank": raw_metrics.blank,
                "single_comments": raw_metrics.single_comments,
            }
        except Exception as e:
            return {
                "error": f"Failed to calculate metrics: {str(e)}",
            }

    def _get_node_name(self, node: ast.AST) -> Optional[str]:
        """
        Get a string representation of an AST node.

        Args:
            node: AST node

        Returns:
            String representation or None
        """
        if node is None:
            return None

        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_str = self._get_node_name(node.value)
            return f"{value_str}.{node.attr}" if value_str else node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Str):
            return node.s
        else:
            try:
                if hasattr(ast, "unparse"):
                    return ast.unparse(node)
            except Exception:
                pass
            return type(node).__name__

    def _get_decorator_name(self, node: ast.AST) -> str:
        """
        Get a string representation of a decorator.

        Args:
            node: AST node (decorator)

        Returns:
            String representation
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_str = self._get_node_name(node.value)
            return f"{value_str}.{node.attr}" if value_str else node.attr
        elif isinstance(node, ast.Call):
            return self._get_node_name(node.func) or "call"
        else:
            try:
                if hasattr(ast, "unparse"):
                    return ast.unparse(node)
            except Exception:
                pass
            return type(node).__name__

    def _extract_classes_regex(self, source_code: str, language: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract classes from non-Python files using regex patterns."""
        classes = []
        
        if language in ["javascript", "typescript", "java", "csharp", "cpp", "c"]:
            pattern = r'(?:public\s+|private\s+|protected\s+|abstract\s+|final\s+)*class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w\s,]+)?\s*\{?'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                class_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                classes.append({
                    "name": class_name,
                    "line_number": line_num,
                    "end_line": None,
                    "docstring": None,
                    "bases": [],
                    "decorators": [],
                    "methods": [],
                    "attributes": [],
                })
        
        elif language == "go":
            pattern = r'type\s+(\w+)\s+(?:struct|interface)\s*\{'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                class_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                classes.append({
                    "name": class_name,
                    "line_number": line_num,
                    "end_line": None,
                    "docstring": None,
                    "bases": [],
                    "decorators": [],
                    "methods": [],
                    "attributes": [],
                })
        
        elif language == "ruby":
            pattern = r'class\s+(\w+)(?:\s+<\s+\w+)?'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                class_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                classes.append({
                    "name": class_name,
                    "line_number": line_num,
                    "end_line": None,
                    "docstring": None,
                    "bases": [],
                    "decorators": [],
                    "methods": [],
                    "attributes": [],
                })
        
        elif language == "php":
            pattern = r'(?:abstract\s+|final\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w\s,]+)?\s*\{'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                class_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                classes.append({
                    "name": class_name,
                    "line_number": line_num,
                    "end_line": None,
                    "docstring": None,
                    "bases": [],
                    "decorators": [],
                    "methods": [],
                    "attributes": [],
                })
        
        elif language == "swift":
            pattern = r'(?:class|struct|enum)\s+(\w+)(?:\s*:\s*[\w\s,]+)?\s*\{'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                class_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                classes.append({
                    "name": class_name,
                    "line_number": line_num,
                    "end_line": None,
                    "docstring": None,
                    "bases": [],
                    "decorators": [],
                    "methods": [],
                    "attributes": [],
                })
        
        elif language in ["kotlin", "scala"]:
            pattern = r'(?:public\s+|private\s+|protected\s+|open\s+|abstract\s+|data\s+|sealed\s+)*class\s+(\w+)(?:\s*\([^)]*\))?(?:\s*:\s*[\w\s,]+)?\s*\{?'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                class_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                classes.append({
                    "name": class_name,
                    "line_number": line_num,
                    "end_line": None,
                    "docstring": None,
                    "bases": [],
                    "decorators": [],
                    "methods": [],
                    "attributes": [],
                })
        
        return classes

    def _extract_functions_regex(self, source_code: str, language: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract functions from non-Python files using regex patterns."""
        functions = []
        
        if language in ["javascript", "typescript"]:
            pattern = r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|async\s*\([^)]*\))\s*=>)'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                func_name = match.group(1) or match.group(2)
                if func_name:
                    line_num = source_code[:match.start()].count('\n') + 1
                    functions.append({
                        "name": func_name,
                        "line_number": line_num,
                        "end_line": None,
                        "docstring": None,
                        "parameter_count": 0,
                        "parameters": [],
                    })
        
        elif language in ["java", "csharp"]:
            pattern = r'(?:public|private|protected|static|\w+)*\s+\w+\s+(\w+)\s*\([^)]*\)'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                func_name = match.group(1)
                if func_name not in ["class", "interface", "enum", "if", "for", "while"]:
                    line_num = source_code[:match.start()].count('\n') + 1
                    param_match = re.search(r'\(([^)]*)\)', source_code[match.start():match.end()])
                    param_count = len([p for p in param_match.group(1).split(',') if p.strip()]) if param_match else 0
                    functions.append({
                        "name": func_name,
                        "line_number": line_num,
                        "end_line": None,
                        "docstring": None,
                        "parameter_count": param_count,
                        "parameters": [],
                    })
        
        elif language == "go":
            pattern = r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\([^)]*\)'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                func_name = match.group(1)
                line_num = source_code[:match.start()].count('\n') + 1
                functions.append({
                    "name": func_name,
                    "line_number": line_num,
                    "end_line": None,
                    "docstring": None,
                    "parameter_count": 0,
                    "parameters": [],
                })
        
        return functions

    def _extract_imports_regex(self, source_code: str, language: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract imports from non-Python files using regex patterns."""
        imports = []
        
        if language in ["javascript", "typescript"]:
            pattern1 = r"import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+)?['\"]([^'\"]+)['\"]"
            for match in re.finditer(pattern1, source_code, re.MULTILINE):
                import_path = match.group(1)
                if import_path and not import_path.startswith('http'):
                    imports.append({
                        "module": import_path,
                        "names": [],
                        "line_number": source_code[:match.start()].count('\n') + 1,
                        "type": "import",
                    })
            
            pattern2 = r"require\(['\"]([^'\"]+)['\"]\)"
            for match in re.finditer(pattern2, source_code, re.MULTILINE):
                import_path = match.group(1)
                if import_path and not import_path.startswith('http'):
                    imports.append({
                        "module": import_path,
                        "names": [],
                        "line_number": source_code[:match.start()].count('\n') + 1,
                        "type": "require",
                    })
            
            pattern3 = r"import\(['\"]([^'\"]+)['\"]\)"
            for match in re.finditer(pattern3, source_code, re.MULTILINE):
                import_path = match.group(1)
                if import_path and not import_path.startswith('http'):
                    imports.append({
                        "module": import_path,
                        "names": [],
                        "line_number": source_code[:match.start()].count('\n') + 1,
                        "type": "dynamic_import",
                    })
        
        elif language == "java":
            pattern = r'import\s+([\w.]+);'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                import_path = match.group(1)
                imports.append({
                    "module": import_path,
                    "names": [],
                    "line_number": source_code[:match.start()].count('\n') + 1,
                })
        
        elif language == "csharp":
            pattern = r'using\s+([\w.]+);'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                import_path = match.group(1)
                imports.append({
                    "module": import_path,
                    "names": [],
                    "line_number": source_code[:match.start()].count('\n') + 1,
                })
        
        elif language == "go":
            pattern = r'import\s+(?:\([^)]+\)|["\']([^"\']+)["\'])'
            for match in re.finditer(pattern, source_code, re.MULTILINE):
                import_path = match.group(1)
                if import_path:
                    imports.append({
                        "module": import_path,
                        "names": [],
                        "line_number": source_code[:match.start()].count('\n') + 1,
                    })
        
        return imports

    def analyze_multiple_files(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple files and return results indexed by file path.

        Args:
            file_paths: List of file paths to analyze

        Returns:
            Dictionary mapping file paths to analysis results
        """
        results = {}
        for file_path in file_paths:
            results[file_path] = self.analyze_file(file_path)
        return results


