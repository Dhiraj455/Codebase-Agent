"""
Code Chunking Service

Chunks Python code into LLM-friendly segments for RAG.
Each chunk contains a class, function group, or module-level code with context.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import ast

from .code_analyzer import CodeAnalyzer


class CodeChunkingService:
    """Service for chunking Python code into semantic units."""

    def __init__(self, code_analyzer: Optional[CodeAnalyzer] = None):
        """
        Initialize the chunking service.

        Args:
            code_analyzer: Optional CodeAnalyzer instance. If not provided, creates a new one.
        """
        self.code_analyzer = code_analyzer or CodeAnalyzer()

    def chunk_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Chunk a Python file into semantic units.

        Args:
            file_path: Path to the Python file

        Returns:
            List of chunk dictionaries with metadata and content
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
                lines = source_code.splitlines()
        except Exception:
            return []

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        # Analyze the file to get structure
        analysis = self.code_analyzer.analyze_file(file_path)
        
        if "error" in analysis:
            return []

        chunks = []

        # Extract imports for context
        imports = self._extract_imports_text(source_code, analysis.get("imports", []))

        # Chunk 1: Module-level imports and variables (only if there are module-level items)
        # Skip if file only has classes/functions (they'll include imports in their chunks)
        has_module_level_code = (
            analysis.get("module_variables") or 
            (not analysis.get("classes") and not analysis.get("functions"))
        )
        
        if has_module_level_code:
            module_chunk = self._create_module_chunk(
                file_path, source_code, lines, imports, analysis
            )
            if module_chunk:
                chunks.append(module_chunk)

        # Chunk 2: Each class as a separate chunk
        for cls in analysis.get("classes", []):
            class_chunk = self._create_class_chunk(
                file_path, source_code, lines, cls, imports, analysis
            )
            if class_chunk:
                chunks.append(class_chunk)

        # Chunk 3: Module-level functions (group related functions)
        functions = analysis.get("functions", [])
        if functions:
            function_chunks = self._create_function_chunks(
                file_path, source_code, lines, functions, imports, analysis
            )
            chunks.extend(function_chunks)

        return chunks

    def _extract_imports_text(
        self, source_code: str, imports: List[Dict[str, Any]]
    ) -> str:
        """
        Extract import statements as text.

        Args:
            source_code: Full source code
            imports: List of import information from analyzer

        Returns:
            String containing all import statements
        """
        lines = source_code.splitlines()
        import_lines = []

        # Get line numbers of imports
        import_line_numbers = {imp["line_number"] for imp in imports}

        # Extract import lines
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if i in import_line_numbers or stripped.startswith(("import ", "from ")):
                import_lines.append(line)

        return "\n".join(import_lines)

    def _create_module_chunk(
        self,
        file_path: str,
        source_code: str,
        lines: List[str],
        imports: str,
        analysis: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Create a chunk for module-level code (imports and variables).

        Args:
            file_path: Path to the file
            source_code: Full source code
            lines: List of source code lines
            imports: Import statements as text
            analysis: Code analysis results

        Returns:
            Module chunk dictionary or None
        """
        module_vars = analysis.get("module_variables", [])
        
        # Only create module chunk if there are module variables or if it's the only content
        if not module_vars and not imports.strip():
            return None

        # Extract module-level variables code
        var_lines = []
        var_line_numbers = {var["line_number"] for var in module_vars}
        
        for i, line in enumerate(lines, start=1):
            if i in var_line_numbers:
                var_lines.append(line)

        content_parts = []
        if imports.strip():
            content_parts.append(imports)
        if var_lines:
            content_parts.append("\n".join(var_lines))

        if not content_parts:
            return None

        content = "\n".join(content_parts)

        return {
            "chunk_id": f"{file_path}::module",
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "chunk_type": "module",
            "name": "module_level",
            "content": content,
            "start_line": 1,
            "end_line": len(var_lines) + len(imports.splitlines()) if var_lines else len(imports.splitlines()),
            "metadata": {
                "import_count": len(analysis.get("imports", [])),
                "variable_count": len(module_vars),
            },
        }

    def _create_class_chunk(
        self,
        file_path: str,
        source_code: str,
        lines: List[str],
        cls: Dict[str, Any],
        imports: str,
        analysis: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Create a chunk for a class (with all its methods).

        Args:
            file_path: Path to the file
            source_code: Full source code
            lines: List of source code lines
            cls: Class information from analysis
            imports: Import statements as text (for context)
            analysis: Code analysis results

        Returns:
            Class chunk dictionary or None
        """
        start_line = cls["line_number"]
        end_line = cls.get("end_line", start_line + 50)  # Fallback if end_line not available

        # Extract class code
        class_lines = lines[start_line - 1 : end_line]

        # Build content with context
        content_parts = []
        
        # Add imports for context
        if imports.strip():
            content_parts.append("# Imports")
            content_parts.append(imports)
            content_parts.append("")

        # Add class docstring if available
        if cls.get("docstring"):
            content_parts.append(f'"""{cls["docstring"]}"""')
            content_parts.append("")

        # Add class definition and body
        class_code = "\n".join(class_lines)
        content_parts.append(class_code)

        content = "\n".join(content_parts)

        return {
            "chunk_id": f"{file_path}::{cls['name']}",
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "chunk_type": "class",
            "name": cls["name"],
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "metadata": {
                "class_name": cls["name"],
                "base_classes": cls.get("bases", []),
                "decorators": cls.get("decorators", []),
                "method_count": len(cls.get("methods", [])),
                "attribute_count": len(cls.get("attributes", [])),
                "docstring": cls.get("docstring"),
            },
        }

    def _create_function_chunks(
        self,
        file_path: str,
        source_code: str,
        lines: List[str],
        functions: List[Dict[str, Any]],
        imports: str,
        analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Create chunks for module-level functions.
        Groups related functions together (functions close to each other).

        Args:
            file_path: Path to the file
            source_code: Full source code
            lines: List of source code lines
            functions: List of function information from analysis
            imports: Import statements as text (for context)
            analysis: Code analysis results

        Returns:
            List of function chunk dictionaries
        """
        if not functions:
            return []

        chunks = []
        
        # Group functions that are close together (within 20 lines)
        function_groups = []
        current_group = [functions[0]]

        for i in range(1, len(functions)):
            prev_func = functions[i - 1]
            curr_func = functions[i]
            
            # If functions are close, group them
            if curr_func["line_number"] - prev_func.get("end_line", prev_func["line_number"]) < 20:
                current_group.append(curr_func)
            else:
                function_groups.append(current_group)
                current_group = [curr_func]

        if current_group:
            function_groups.append(current_group)

        # Create a chunk for each group
        for group in function_groups:
            if len(group) == 1:
                # Single function chunk
                chunk = self._create_single_function_chunk(
                    file_path, source_code, lines, group[0], imports, analysis
                )
            else:
                # Multiple functions chunk
                chunk = self._create_function_group_chunk(
                    file_path, source_code, lines, group, imports, analysis
                )
            
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_single_function_chunk(
        self,
        file_path: str,
        source_code: str,
        lines: List[str],
        func: Dict[str, Any],
        imports: str,
        analysis: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Create a chunk for a single function.

        Args:
            file_path: Path to the file
            source_code: Full source code
            lines: List of source code lines
            func: Function information from analysis
            imports: Import statements as text (for context)
            analysis: Code analysis results

        Returns:
            Function chunk dictionary or None
        """
        start_line = func["line_number"]
        end_line = func.get("end_line", start_line + 30)  # Fallback

        # Extract function code
        func_lines = lines[start_line - 1 : end_line]

        # Build content with context
        content_parts = []
        
        # Add imports for context
        if imports.strip():
            content_parts.append("# Imports")
            content_parts.append(imports)
            content_parts.append("")

        # Add function docstring if available
        if func.get("docstring"):
            content_parts.append(f'"""{func["docstring"]}"""')
            content_parts.append("")

        # Add function code
        func_code = "\n".join(func_lines)
        content_parts.append(func_code)

        content = "\n".join(content_parts)

        return {
            "chunk_id": f"{file_path}::{func['name']}",
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "chunk_type": "function",
            "name": func["name"],
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "metadata": {
                "function_name": func["name"],
                "parameters": func.get("parameters", []),
                "parameter_count": func.get("parameter_count", 0),
                "return_annotation": func.get("return_annotation"),
                "decorators": func.get("decorators", []),
                "is_async": func.get("is_async", False),
                "docstring": func.get("docstring"),
            },
        }

    def _create_function_group_chunk(
        self,
        file_path: str,
        source_code: str,
        lines: List[str],
        functions: List[Dict[str, Any]],
        imports: str,
        analysis: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Create a chunk for a group of related functions.

        Args:
            file_path: Path to the file
            source_code: Full source code
            lines: List of source code lines
            functions: List of function information from analysis
            imports: Import statements as text (for context)
            analysis: Code analysis results

        Returns:
            Function group chunk dictionary or None
        """
        if not functions:
            return None

        start_line = functions[0]["line_number"]
        end_line = functions[-1].get("end_line", functions[-1]["line_number"] + 30)

        # Extract all function code
        func_lines = lines[start_line - 1 : end_line]

        # Build content with context
        content_parts = []
        
        # Add imports for context
        if imports.strip():
            content_parts.append("# Imports")
            content_parts.append(imports)
            content_parts.append("")

        # Add function code
        func_code = "\n".join(func_lines)
        content_parts.append(func_code)

        content = "\n".join(content_parts)

        function_names = [f["name"] for f in functions]

        return {
            "chunk_id": f"{file_path}::functions_{start_line}",
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "chunk_type": "function_group",
            "name": f"functions_{'_'.join(function_names[:3])}",  # First 3 function names
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "metadata": {
                "function_names": function_names,
                "function_count": len(functions),
                "functions": [
                    {
                        "name": f["name"],
                        "line_number": f["line_number"],
                        "parameter_count": f.get("parameter_count", 0),
                    }
                    for f in functions
                ],
            },
        }

    def chunk_multiple_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Chunk multiple files and return all chunks.

        Args:
            file_paths: List of file paths to chunk

        Returns:
            List of all chunks from all files
        """
        all_chunks = []
        for file_path in file_paths:
            chunks = self.chunk_file(file_path)
            all_chunks.extend(chunks)
        return all_chunks

    def get_chunk_summary(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get a summary of chunks.

        Args:
            chunks: List of chunks

        Returns:
            Summary dictionary
        """
        chunk_types = {}
        total_content_length = 0

        for chunk in chunks:
            chunk_type = chunk["chunk_type"]
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            total_content_length += len(chunk.get("content", ""))

        return {
            "total_chunks": len(chunks),
            "chunk_types": chunk_types,
            "total_content_length": total_content_length,
            "average_chunk_length": total_content_length / len(chunks) if chunks else 0,
        }


# Example usage
if __name__ == "__main__":
    chunking_service = CodeChunkingService()

    # Example: Chunk a file
    # chunks = chunking_service.chunk_file("path/to/file.py")
    # 
    # print(f"Created {len(chunks)} chunks")
    # for chunk in chunks:
    #     print(f"\nChunk: {chunk['name']} ({chunk['chunk_type']})")
    #     print(f"Lines: {chunk['start_line']}-{chunk['end_line']}")
    #     print(f"Content preview: {chunk['content'][:100]}...")
