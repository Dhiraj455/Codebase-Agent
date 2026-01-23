"""
Static Code Analysis Service using AST

Analyzes Python files to extract classes, functions, imports, and complexity metrics.
"""

import ast
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze


class CodeAnalyzer:
    """Service for static code analysis using AST parsing."""

    def __init__(self):
        """Initialize the code analyzer."""
        pass

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a Python file and extract structured information.

        Args:
            file_path: Path to the Python file

        Returns:
            Dictionary containing:
            {
                "file_path": "...",
                "file_name": "...",
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
        
        if not file_path_obj.exists():
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "error": f"File does not exist: {file_path}",
            }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
        except Exception as e:
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "error": f"Failed to read file: {str(e)}",
            }

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "error": f"Syntax error: {str(e)}",
                "syntax_error_line": e.lineno,
            }
        except Exception as e:
            return {
                "file_path": str(file_path),
                "file_name": file_path_obj.name,
                "error": f"Failed to parse AST: {str(e)}",
            }

        # Extract information
        classes = self._extract_classes(tree, source_code)
        functions = self._extract_functions(tree, source_code)
        imports = self._extract_imports(tree)
        module_variables = self._extract_module_variables(tree, source_code)

        # Calculate complexity metrics
        complexity_metrics = self._calculate_complexity(source_code, file_path)
        code_metrics = self._calculate_code_metrics(source_code)

        return {
            "file_path": str(file_path),
            "file_name": file_path_obj.name,
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "module_variables": module_variables,
            "complexity": complexity_metrics,
            "metrics": code_metrics,
            "line_count": len(source_code.splitlines()),
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

                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = self._extract_function_info(item, source_code)
                        class_info["methods"].append(method_info)

                    # Extract class-level assignments (attributes)
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
            # Only get top-level functions (not methods inside classes)
            if isinstance(node, ast.FunctionDef):
                # Check if this function is inside a class
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
        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param_info = {
                "name": arg.arg,
                "annotation": self._get_node_name(arg.annotation) if arg.annotation else None,
            }
            parameters.append(param_info)

        # Extract return annotation
        return_annotation = None
        if node.returns:
            return_annotation = self._get_node_name(node.returns)

        # Check for decorators
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]

        # Count statements in function body
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

                    # Check if there's a type annotation (for typed assignments)
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
            # Calculate cyclomatic complexity
            complexity_results = cc_visit(source_code)
            
            # Organize by function/class
            complexity_by_function = []
            for item in complexity_results:
                complexity_by_function.append({
                    "name": item.name,
                    "complexity": item.complexity,
                    "rank": item.rank,
                    "line_number": item.lineno,
                    "type": item.type,  # 'function' or 'method'
                })

            # Calculate maintainability index
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
                "loc": raw_metrics.loc,  # Lines of code
                "lloc": raw_metrics.lloc,  # Logical lines of code
                "sloc": raw_metrics.sloc,  # Source lines of code
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
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        else:
            # Try ast.unparse (Python 3.9+), fallback to type name
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
            # Try ast.unparse (Python 3.9+), fallback to type name
            try:
                if hasattr(ast, "unparse"):
                    return ast.unparse(node)
            except Exception:
                pass
            return type(node).__name__

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


# Example usage
if __name__ == "__main__":
    analyzer = CodeAnalyzer()

    # Example: Analyze a file
    example_file = Path(__file__)  # Analyze this file itself
    result = analyzer.analyze_file(str(example_file))

    print(f"File: {result['file_name']}")
    print(f"\nClasses: {len(result['classes'])}")
    for cls in result['classes']:
        print(f"  - {cls['name']} ({len(cls['methods'])} methods)")

    print(f"\nFunctions: {len(result['functions'])}")
    for func in result['functions']:
        print(f"  - {func['name']} ({func['parameter_count']} params)")

    print(f"\nImports: {len(result['imports'])}")
    print(f"\nComplexity Metrics:")
    print(f"  Average: {result['complexity'].get('average_complexity', 'N/A')}")
    print(f"  Max: {result['complexity'].get('max_complexity', 'N/A')}")
