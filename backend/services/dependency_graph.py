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


class DependencyGraphBuilder:
    """Service for building dependency graphs from code analysis."""

    def __init__(self, code_analyzer: Optional[CodeAnalyzer] = None):
        """
        Initialize the dependency graph builder.

        Args:
            code_analyzer: Optional CodeAnalyzer instance. If not provided, creates a new one.
        """
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.file_graph = nx.DiGraph()  # Directed graph for file dependencies
        self.function_graph = nx.DiGraph()  # Directed graph for function calls

    def build_file_dependency_graph(
        self, repo_path: str, python_files: List[Dict[str, str]]
    ) -> nx.DiGraph:
        """
        Build file-level dependency graph based on imports.

        Args:
            repo_path: Path to the repository root
            python_files: List of file dictionaries from repo_ingestion

        Returns:
            NetworkX directed graph with file dependencies
        """
        self.file_graph = nx.DiGraph()
        repo_path_obj = Path(repo_path)

        # Map module names to file paths
        module_to_file = {}
        file_to_module = {}

        # First pass: map files to module names
        for file_info in python_files:
            file_path = Path(file_info["absolute_path"])
            relative_path = file_info["path"]
            
            # Convert file path to module name
            module_name = self._file_path_to_module_name(relative_path)
            module_to_file[module_name] = file_path
            file_to_module[str(file_path)] = module_name

            # Add node to graph
            self.file_graph.add_node(
                str(file_path),
                name=file_path.name,
                relative_path=relative_path,
                module_name=module_name,
            )

        # Second pass: analyze imports and create edges
        for file_info in python_files:
            file_path = file_info["absolute_path"]
            
            try:
                analysis = self.code_analyzer.analyze_file(file_path)
                
                if "error" in analysis:
                    continue

                # Process imports
                for import_info in analysis.get("imports", []):
                    target_module = self._resolve_import(
                        import_info,
                        file_path,
                        repo_path_obj,
                        module_to_file,
                        file_to_module,
                    )

                    if target_module:
                        # Add edge: current file depends on target file
                        if target_module in self.file_graph:
                            self.file_graph.add_edge(file_path, target_module)

            except Exception as e:
                # Skip files that can't be analyzed
                continue

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

                # Process functions and methods
                for func in analysis.get("functions", []):
                    func_id = f"{file_path}::{func['name']}"
                    self.function_graph.add_node(
                        func_id,
                        name=func["name"],
                        file=file_path,
                        line_number=func["line_number"],
                        type="function",
                    )

                # Process classes and their methods
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

                # TODO: Parse function bodies to detect actual calls
                # This would require more sophisticated AST analysis
                # For now, we create the nodes but don't add call edges

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
            # Find all simple cycles
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except Exception:
            # NetworkX might not have simple_cycles for all graph types
            # Fallback: use strongly connected components
            sccs = list(nx.strongly_connected_components(graph))
            # Filter out single-node components
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

        # Convert nodes to list with metadata
        nodes = []
        for node_id in graph.nodes():
            node_data = {
                "id": node_id,
            }
            
            if include_metadata:
                # Get node attributes
                attrs = graph.nodes[node_id]
                node_data.update({
                    "name": attrs.get("name", Path(node_id).name),
                    "relative_path": attrs.get("relative_path", str(node_id)),
                    "module_name": attrs.get("module_name", ""),
                })

            nodes.append(node_data)

        # Convert edges to list
        edges = []
        for source, target in graph.edges():
            edge_data = {
                "source": source,
                "target": target,
            }
            edges.append(edge_data)

        # Detect cycles
        cycles = self.detect_circular_dependencies(graph)

        # Get statistics
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
        # Remove .py extension
        module_path = file_path.replace(".py", "")
        # Replace path separators with dots
        module_name = module_path.replace("/", ".").replace("\\", ".")
        # Remove __init__ suffix if present
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]
        return module_name

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
            # import module
            module_name = import_info["module"]
            
            # Try direct match
            if module_name in module_to_file:
                return str(module_to_file[module_name])

            # Try with __init__.py
            init_module = f"{module_name}.__init__"
            if init_module in module_to_file:
                return str(module_to_file[init_module])

            # Try partial matches (for submodules)
            for mod_name, file_path in module_to_file.items():
                if mod_name.startswith(module_name + ".") or mod_name == module_name:
                    return str(file_path)

        elif import_info["type"] == "from_import":
            # from module import name
            module_name = import_info["module"]
            
            if not module_name:
                # Relative import: from . import something
                # For now, skip relative imports (complex to resolve)
                return None

            # Try direct match
            if module_name in module_to_file:
                return str(module_to_file[module_name])

            # Try with __init__.py
            init_module = f"{module_name}.__init__"
            if init_module in module_to_file:
                return str(module_to_file[init_module])

            # Try partial matches (for submodules)
            for mod_name, file_path in module_to_file.items():
                if mod_name.startswith(module_name + ".") or mod_name == module_name:
                    return str(file_path)

            # Try relative import from source directory
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

        # Files this file depends on (outgoing edges)
        dependencies = list(self.file_graph.successors(file_path))

        # Files that depend on this file (incoming edges)
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
            # Graph has cycles, can't do topological sort
            return []


# Example usage
if __name__ == "__main__":
    from .repo_ingestion import RepoIngestionService

    # Example: Build dependency graph for a repository
    repo_service = RepoIngestionService()
    graph_builder = DependencyGraphBuilder()

    # This would be used with actual repo analysis
    # result = repo_service.process_repo("https://github.com/user/repo")
    # graph = graph_builder.build_file_dependency_graph(
    #     result["repo_path"], result["files"]
    # )
    # 
    # json_output = graph_builder.export_graph_to_json()
    # print(f"Nodes: {json_output['statistics']['nodes']}")
    # print(f"Edges: {json_output['statistics']['edges']}")
    # print(f"Cycles: {len(json_output['cycles'])}")
