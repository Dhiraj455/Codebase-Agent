

from pathlib import Path
from typing import Dict, List, Optional, Any
import ast

from .code_analyzer import CodeAnalyzer


class CodeChunkingService:


    def __init__(self, code_analyzer: Optional[CodeAnalyzer] = None):

        self.code_analyzer = code_analyzer or CodeAnalyzer()

    def chunk_file(self, file_path: str) -> List[Dict[str, Any]]:

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

        analysis = self.code_analyzer.analyze_file(file_path)

        if "error" in analysis:
            return []

        chunks = []

        imports = self._extract_imports_text(source_code, analysis.get("imports", []))

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

        for cls in analysis.get("classes", []):
            class_chunk = self._create_class_chunk(
                file_path, source_code, lines, cls, imports, analysis
            )
            if class_chunk:
                chunks.append(class_chunk)

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

        lines = source_code.splitlines()
        import_lines = []

        import_line_numbers = {imp["line_number"] for imp in imports}

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

        module_vars = analysis.get("module_variables", [])

        if not module_vars and not imports.strip():
            return None

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

        start_line = cls["line_number"]
        end_line = cls.get("end_line", start_line + 50)

        class_lines = lines[start_line - 1 : end_line]

        content_parts = []

        if imports.strip():
            content_parts.append(imports)
            content_parts.append("")

        if cls.get("docstring"):
            content_parts.append(cls.get("docstring"))
            content_parts.append("")

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

        if not functions:
            return []

        chunks = []

        function_groups = []
        current_group = [functions[0]]

        for i in range(1, len(functions)):
            prev_func = functions[i - 1]
            curr_func = functions[i]

            if curr_func["line_number"] - prev_func.get("end_line", prev_func["line_number"]) < 20:
                current_group.append(curr_func)
            else:
                function_groups.append(current_group)
                current_group = [curr_func]

        if current_group:
            function_groups.append(current_group)

        for group in function_groups:
            if len(group) == 1:
                chunk = self._create_single_function_chunk(
                    file_path, source_code, lines, group[0], imports, analysis
                )
            else:
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

        start_line = func["line_number"]
        end_line = func.get("end_line", start_line + 30)

        func_lines = lines[start_line - 1 : end_line]

        content_parts = []

        if imports.strip():
            content_parts.append(imports)
            content_parts.append("")

        if func.get("docstring"):
            content_parts.append(func.get("docstring"))
            content_parts.append("")

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

        if not functions:
            return None

        start_line = functions[0]["line_number"]
        end_line = functions[-1].get("end_line", functions[-1]["line_number"] + 30)

        func_lines = lines[start_line - 1 : end_line]

        content_parts = []

        if imports.strip():
            content_parts.append(imports)
            content_parts.append("")

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

        all_chunks = []
        for file_path in file_paths:
            chunks = self.chunk_file(file_path)
            all_chunks.extend(chunks)
        return all_chunks

    def chunk_text_file(self, file_path: str, max_chunk_size: int = 2000) -> List[Dict[str, Any]]:

        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
                lines = source_code.splitlines()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []

        chunks = []
        current_chunk_lines = []
        current_chunk_size = 0
        chunk_start_line = 1

        for i, line in enumerate(lines, start=1):
            line_size = len(line) + 1

            if current_chunk_size + line_size > max_chunk_size and current_chunk_lines:
                chunk_content = "\n".join(current_chunk_lines)
                chunks.append({
                    "chunk_id": f"{file_path}::chunk_{len(chunks) + 1}",
                    "file_path": file_path,
                    "file_name": file_path_obj.name,
                    "chunk_type": "text",
                    "name": f"{file_path_obj.stem}_chunk_{len(chunks) + 1}",
                    "content": chunk_content,
                    "start_line": chunk_start_line,
                    "end_line": i - 1,
                    "metadata": {
                        "file_extension": file_path_obj.suffix,
                        "language": self._detect_language(file_path_obj.suffix),
                    },
                })

                current_chunk_lines = [line]
                current_chunk_size = line_size
                chunk_start_line = i
            else:
                current_chunk_lines.append(line)
                current_chunk_size += line_size

        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            chunks.append({
                "chunk_id": f"{file_path}::chunk_{len(chunks) + 1}",
                "file_path": file_path,
                "file_name": file_path_obj.name,
                "chunk_type": "text",
                "name": f"{file_path_obj.stem}_chunk_{len(chunks) + 1}",
                "content": chunk_content,
                "start_line": chunk_start_line,
                "end_line": len(lines),
                "metadata": {
                    "file_extension": file_path_obj.suffix,
                    "language": self._detect_language(file_path_obj.suffix),
                },
            })

        return chunks

    def _detect_language(self, extension: str) -> str:

        language_map = {
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".html": "HTML",
            ".css": "CSS",
            ".json": "JSON",
            ".md": "Markdown",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
        }
        return language_map.get(extension.lower(), "Unknown")

    def get_chunk_summary(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:

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


if __name__ == "__main__":
    chunking_service = CodeChunkingService()

