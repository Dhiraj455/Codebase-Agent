"""
Dependency Graph Builder Service

Builds dependency graphs at file and function levels using NetworkX.
Detects circular dependencies and exports graph data.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
import networkx as nx
from collections import defaultdict

from .code_analyzer import CodeAnalyzer
from .multi_lang_analyzer import MultiLanguageAnalyzer


class DependencyGraphBuilder:
    """Service for building dependency graphs from code analysis."""

    def __init__(self, code_analyzer: Optional[CodeAnalyzer] = None):
        """
        Initialize the dependency graph builder.

        Args:
            code_analyzer: Optional CodeAnalyzer instance. If not provided, creates a new one.
        """
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.multi_lang_analyzer = MultiLanguageAnalyzer()
        self.file_graph = nx.DiGraph()
        self.function_graph = nx.DiGraph()

    def build_file_dependency_graph(
        self, repo_path: str, code_files: List[Dict[str, str]]
    ) -> nx.DiGraph:
        """
        Build file-level dependency graph based on imports.
        Supports Python, JavaScript, TypeScript, and other languages.

        Args:
            repo_path: Path to the repository root
            code_files: List of file dictionaries from repo_ingestion (can be any language)

        Returns:
            NetworkX directed graph with file dependencies
        """
        self.file_graph = nx.DiGraph()
        repo_path_obj = Path(repo_path)

        module_to_file = {}
        file_to_module = {}
        file_languages = {}

        for file_info in code_files:
            file_path = Path(file_info["absolute_path"])
            relative_path = file_info["path"]
            
            extension = file_path.suffix.lower()
            language = self.multi_lang_analyzer._detect_language(extension)
            file_languages[str(file_path)] = language
            
            if language == "python":
                module_name = self._file_path_to_module_name(relative_path)
                module_to_file[module_name] = file_path
                file_to_module[str(file_path)] = module_name
            else:
                module_name = self._file_path_to_module_name_js(relative_path, extension)
                
                variations = [
                    module_name,
                    "./" + module_name,
                    module_name + "/index",
                    "./" + module_name + "/index",
                ]
                
                for ext in ["", ".js", ".jsx", ".ts", ".tsx"]:
                    if ext:
                        variations.extend([
                            module_name + ext,
                            "./" + module_name + ext,
                        ])
                
                for var in variations:
                    module_to_file[var] = file_path
                
                file_to_module[str(file_path)] = module_name

            self.file_graph.add_node(
                str(file_path),
                name=file_path.name,
                relative_path=relative_path,
                module_name=module_name,
                language=language,
            )

        edges_created = 0
        files_with_imports = 0
        files_without_imports = 0
        
        for file_info in code_files:
            file_path = file_info["absolute_path"]
            language = file_languages.get(file_path, "unknown")
            
            try:
                analysis = self.code_analyzer.analyze_file(file_path)
                if "error" in analysis:
                    print(f"  ⚠ Error analyzing {Path(file_path).name}: {analysis.get('error', 'Unknown error')}")
                    continue
                
                imports = analysis.get("imports", [])
                
                if imports:
                    files_with_imports += 1
                    print(f"Analyzing {Path(file_path).name} ({language}): {len(imports)} imports found")
                else:
                    files_without_imports += 1

                for import_info in imports:
                    if isinstance(import_info, dict):
                        module_name = import_info.get("module") or import_info.get("name", "")
                    elif isinstance(import_info, str):
                        module_name = import_info
                    else:
                        continue
                    
                    if not module_name:
                        continue
                    
                    target_file = self._resolve_dependency(
                        {"module": module_name} if isinstance(module_name, str) else import_info,
                        file_path,
                        repo_path_obj,
                        module_to_file,
                        file_to_module,
                        language,
                    )

                    if target_file and target_file in self.file_graph:
                        self.file_graph.add_edge(file_path, target_file)
                        edges_created += 1
                        print(f"  ✓ Edge: {Path(file_path).name} -> {Path(target_file).name}")
                    elif target_file:
                        print(f"  ⚠ Skipped (not in graph): {Path(file_path).name} -> {module_name}")
                    else:
                        pass

            except Exception as e:
                print(f"  ✗ Error analyzing {Path(file_path).name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n{'='*60}")
        print(f"Dependency Graph Summary:")
        print(f"  - Files analyzed: {len(code_files)}")
        print(f"  - Files with imports: {files_with_imports}")
        print(f"  - Files without imports: {files_without_imports}")
        print(f"  - Edges created: {edges_created}")
        print(f"  - Nodes in graph: {self.file_graph.number_of_nodes()}")
        print(f"{'='*60}\n")
        
        print(f"Created {edges_created} edges total")
        return self.file_graph

    def build_function_call_graph(
        self, repo_path: str, python_files: List[Dict[str, str]]
    ) -> nx.DiGraph:
        """
        Build function-level call graph (advanced feature).

        Args:
            repo_path: Path to the repository root
            python_files: List of file dictionaries from repo_ingestion

        Returns:
            NetworkX directed graph with function call dependencies
        """
        self.function_graph = nx.DiGraph()

        for file_info in python_files:
            file_path = file_info["absolute_path"]

            try:
                analysis = self.code_analyzer.analyze_file(file_path)
                
                if "error" in analysis:
                    continue

                for func in analysis.get("functions", []):
                    func_id = f"{file_path}::{func['name']}"
                    self.function_graph.add_node(
                        func_id,
                        name=func["name"],
                        file=file_path,
                        line_number=func["line_number"],
                        type="function",
                    )

                for cls in analysis.get("classes", []):
                    for method in cls.get("methods", []):
                        method_id = f"{file_path}::{cls['name']}.{method['name']}"
                        self.function_graph.add_node(
                            method_id,
                            name=f"{cls['name']}.{method['name']}",
                            file=file_path,
                            class_name=cls["name"],
                            line_number=method["line_number"],
                            type="method",
                        )


            except Exception as e:
                continue

        return self.function_graph

    def detect_circular_dependencies(
        self, graph: Optional[nx.DiGraph] = None
    ) -> List[List[str]]:
        """
        Detect circular dependencies in the graph.

        Args:
            graph: NetworkX graph to analyze. If None, uses file_graph.

        Returns:
            List of cycles, where each cycle is a list of node names
        """
        if graph is None:
            graph = self.file_graph

        try:
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except Exception:
            sccs = list(nx.strongly_connected_components(graph))
            cycles = [list(scc) for scc in sccs if len(scc) > 1]
            return cycles

    def get_graph_statistics(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        """
        Get statistics about the dependency graph.

        Args:
            graph: NetworkX graph to analyze. If None, uses file_graph.

        Returns:
            Dictionary with graph statistics
        """
        if graph is None:
            graph = self.file_graph

        if len(graph.nodes) == 0:
            return {
                "nodes": 0,
                "edges": 0,
                "density": 0.0,
                "is_dag": True,
            }

        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "density": nx.density(graph),
            "is_dag": nx.is_directed_acyclic_graph(graph),
            "strongly_connected_components": len(list(nx.strongly_connected_components(graph))),
            "weakly_connected_components": len(list(nx.weakly_connected_components(graph))),
        }

    def export_graph_to_json(
        self, graph: Optional[nx.DiGraph] = None, include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Export graph to JSON format for frontend visualization.

        Args:
            graph: NetworkX graph to export. If None, uses file_graph.
            include_metadata: Whether to include node metadata

        Returns:
            Dictionary with nodes and edges in JSON-serializable format
        """
        if graph is None:
            graph = self.file_graph

        nodes = []
        for node_id in graph.nodes():
            node_data = {
                "id": node_id,
            }
            
            if include_metadata:
                attrs = graph.nodes[node_id]
                node_data.update({
                    "name": attrs.get("name", Path(node_id).name),
                    "relative_path": attrs.get("relative_path", str(node_id)),
                    "module_name": attrs.get("module_name", ""),
                })

            nodes.append(node_data)

        edges = []
        for source, target in graph.edges():
            edge_data = {
                "source": source,
                "target": target,
            }
            edges.append(edge_data)

        cycles = self.detect_circular_dependencies(graph)

        stats = self.get_graph_statistics(graph)

        return {
            "nodes": nodes,
            "edges": edges,
            "cycles": cycles,
            "statistics": stats,
        }

    def _file_path_to_module_name(self, file_path: str) -> str:
        """
        Convert file path to Python module name.

        Args:
            file_path: Relative file path (e.g., "src/utils/helper.py")

        Returns:
            Module name (e.g., "src.utils.helper")
        """
        module_path = file_path.replace(".py", "")
        module_name = module_path.replace("/", ".").replace("\\", ".")
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        return module_name
    
    def _file_path_to_module_name_js(self, file_path: str, extension: str) -> str:
        """
        Convert file path to JavaScript/TypeScript module identifier.
        Creates multiple possible identifiers for matching.

        Args:
            file_path: Relative file path (e.g., "src/utils/helper.js")
            extension: File extension (e.g., ".js", ".tsx")

        Returns:
            Module identifier (e.g., "src/utils/helper" or "./src/utils/helper")
        """
        module_path = file_path
        for ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]:
            if module_path.endswith(ext):
                module_path = module_path[:-len(ext)]
                break
        
        module_path = module_path.replace("\\", "/")
        
        return module_path

    def _resolve_dependency(
        self,
        import_info: Dict[str, Any],
        source_file: str,
        repo_path: Path,
        module_to_file: Dict[str, Path],
        file_to_module: Dict[str, str],
        language: str,
    ) -> Optional[str]:
        """
        Resolve a dependency/import statement to an actual file path.
        Supports Python, JavaScript, TypeScript, and other languages.

        Args:
            import_info: Import/dependency information
            source_file: Path to the file containing the import
            repo_path: Repository root path
            module_to_file: Mapping of module names to file paths
            file_to_module: Mapping of file paths to module names
            language: Programming language of the source file

        Returns:
            Resolved file path or None if not found
        """
        if language == "python":
            return self._resolve_import(
                import_info, source_file, repo_path, module_to_file, file_to_module
            )
        elif language in ["javascript", "typescript"]:
            return self._resolve_js_import(
                import_info, source_file, repo_path, module_to_file, file_to_module
            )
        else:
            return self._resolve_generic_import(
                import_info, source_file, repo_path, module_to_file, file_to_module
            )
    
    def _resolve_import(
        self,
        import_info: Dict[str, Any],
        source_file: str,
        repo_path: Path,
        module_to_file: Dict[str, Path],
        file_to_module: Dict[str, str],
    ) -> Optional[str]:
        """
        Resolve an import statement to an actual file path.

        Args:
            import_info: Import information from code_analyzer
            source_file: Path to the file containing the import
            repo_path: Repository root path
            module_to_file: Mapping of module names to file paths
            file_to_module: Mapping of file paths to module names

        Returns:
            Resolved file path or None if not found
        """
        source_path = Path(source_file)
        source_dir = source_path.parent

        if import_info["type"] == "import":
            module_name = import_info["module"]
            
            if module_name in module_to_file:
                return str(module_to_file[module_name])

            init_module = f"{module_name}.__init__"
            if init_module in module_to_file:
                return str(module_to_file[init_module])

            for mod_name, file_path in module_to_file.items():
                if mod_name.startswith(module_name + ".") or mod_name == module_name:
                    return str(file_path)

        elif import_info["type"] == "from_import":
            module_name = import_info["module"]
            
            if not module_name:
                return None

            if module_name in module_to_file:
                return str(module_to_file[module_name])

            init_module = f"{module_name}.__init__"
            if init_module in module_to_file:
                return str(module_to_file[init_module])

            for mod_name, file_path in module_to_file.items():
                if mod_name.startswith(module_name + ".") or mod_name == module_name:
                    return str(file_path)

            module_parts = module_name.split(".")
            potential_path = source_dir
            for part in module_parts:
                potential_path = potential_path / part
                py_file = potential_path.with_suffix(".py")
                init_file = potential_path / "__init__.py"
                
                if py_file.exists() and str(py_file) in file_to_module:
                    return str(py_file)
                if init_file.exists() and str(init_file) in file_to_module:
                    return str(init_file)

        return None
    
    def _resolve_js_import(
        self,
        import_info: Dict[str, Any],
        source_file: str,
        repo_path: Path,
        module_to_file: Dict[str, Path],
        file_to_module: Dict[str, str],
    ) -> Optional[str]:
        """
        Resolve a JavaScript/TypeScript import/require to an actual file path.
        
        Args:
            import_info: Import information with 'module' field
            source_file: Path to the file containing the import
            repo_path: Repository root path
            module_to_file: Mapping of module names to file paths
            file_to_module: Mapping of file paths to module names
            
        Returns:
            Resolved file path or None if not found
        """
        module_name = import_info.get("module", "")
        if not module_name:
            return None
        
        if not module_name.startswith(".") and "/" not in module_name:
            return None
        
        source_path = Path(source_file)
        source_dir = source_path.parent
        
        if module_name.startswith("."):
            try:
                resolved_path = (source_dir / module_name).resolve()
                
                for ext in ["", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]:
                    potential_file = resolved_path.with_suffix(ext) if ext else resolved_path
                    if potential_file.exists():
                        potential_file_str = str(potential_file)
                        if potential_file_str in file_to_module:
                            return potential_file_str
                
                if resolved_path.is_dir():
                    for index_file in ["index.js", "index.jsx", "index.ts", "index.tsx"]:
                        potential_file = resolved_path / index_file
                        if potential_file.exists():
                            potential_file_str = str(potential_file)
                            if potential_file_str in file_to_module:
                                return potential_file_str
            except Exception:
                pass
        
        if module_name in module_to_file:
            return str(module_to_file[module_name])
        
        for ext in ["", ".js", ".jsx", ".ts", ".tsx"]:
            module_with_ext = module_name + ext
            if module_with_ext in module_to_file:
                return str(module_to_file[module_with_ext])
        
        try:
            module_parts = module_name.split("/")
            potential_path = repo_path
            for part in module_parts:
                if part == ".." or part == ".":
                    continue
                potential_path = potential_path / part
            
            for ext in ["", ".js", ".jsx", ".ts", ".tsx"]:
                potential_file = potential_path.with_suffix(ext) if ext else potential_path
                if potential_file.exists():
                    potential_file_str = str(potential_file)
                    if potential_file_str in file_to_module:
                        return potential_file_str
            
            if potential_path.is_dir():
                for index_file in ["index.js", "index.jsx", "index.ts", "index.tsx"]:
                    potential_file = potential_path / index_file
                    if potential_file.exists():
                        potential_file_str = str(potential_file)
                        if potential_file_str in file_to_module:
                            return potential_file_str
        except Exception:
            pass
        
        module_name_clean = module_name.lstrip("./")
        for mod_name, file_path in module_to_file.items():
            mod_name_clean_check = mod_name.lstrip("./")
            if mod_name_clean_check.endswith(module_name_clean) or module_name_clean.endswith(mod_name_clean_check):
                return str(file_path)
        
        return None
    
    def _resolve_generic_import(
        self,
        import_info: Dict[str, Any],
        source_file: str,
        repo_path: Path,
        module_to_file: Dict[str, Path],
        file_to_module: Dict[str, str],
    ) -> Optional[str]:
        """
        Generic import resolution for other languages.
        
        Args:
            import_info: Import information
            source_file: Path to the file containing the import
            repo_path: Repository root path
            module_to_file: Mapping of module names to file paths
            file_to_module: Mapping of file paths to module names
            
        Returns:
            Resolved file path or None if not found
        """
        module_name = import_info.get("module", "")
        if not module_name:
            return None
        
        if module_name in module_to_file:
            return str(module_to_file[module_name])
        
        for mod_name, file_path in module_to_file.items():
            if mod_name.endswith(module_name) or module_name in mod_name:
                return str(file_path)
        
        return None

    def get_file_dependencies(self, file_path: str) -> Dict[str, List[str]]:
        """
        Get dependencies for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with 'dependencies' (files this file imports)
            and 'dependents' (files that import this file)
        """
        if file_path not in self.file_graph:
            return {
                "dependencies": [],
                "dependents": [],
            }

        dependencies = list(self.file_graph.successors(file_path))

        dependents = list(self.file_graph.predecessors(file_path))

        return {
            "dependencies": dependencies,
            "dependents": dependents,
        }

    def get_topological_order(self) -> List[str]:
        """
        Get files in topological order (dependency order).

        Returns:
            List of file paths in topological order
        """
        try:
            return list(nx.topological_sort(self.file_graph))
        except nx.NetworkXError:
            return []


