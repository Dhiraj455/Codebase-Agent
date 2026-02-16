import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class MultiLanguageAnalyzer:

    def __init__(self):
        pass

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {"error": "File not found"}
        
        # Detect language from extension
        extension = file_path_obj.suffix.lower()
        language = self._detect_language(extension)
        
        if not language:
            return {"error": f"Unsupported file type: {extension}"}
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source_code = f.read()
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}
        
        # Extract dependencies based on language
        dependencies = []
        
        if language == "python":
            dependencies = self._extract_python_imports(source_code)
        elif language in ["javascript", "typescript"]:
            dependencies = self._extract_js_imports(source_code, file_path)
        elif language == "java":
            dependencies = self._extract_java_imports(source_code)
        elif language == "go":
            dependencies = self._extract_go_imports(source_code)
        elif language == "rust":
            dependencies = self._extract_rust_imports(source_code)
        else:
            # Generic extraction for other languages
            dependencies = self._extract_generic_imports(source_code, language)
        
        return {
            "file_path": file_path,
            "relative_path": str(file_path_obj),
            "language": language,
            "extension": extension,
            "dependencies": dependencies,
            "error": None,
        }
    
    def _detect_language(self, extension: str) -> Optional[str]:
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
        }
        return language_map.get(extension)
    
    def _extract_python_imports(self, source_code: str) -> List[Dict[str, Any]]:
        imports = []
        
        # Pattern for: import module
        import_pattern = r'^import\s+([a-zA-Z0-9_.]+)'
        # Pattern for: from module import name
        from_import_pattern = r'^from\s+([a-zA-Z0-9_.]+)\s+import\s+'
        
        lines = source_code.split('\n')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
            
            # Match: import module
            match = re.match(import_pattern, stripped)
            if match:
                module = match.group(1)
                imports.append({
                    "type": "import",
                    "module": module,
                    "line_number": i,
                })
                continue
            
            # Match: from module import ...
            match = re.match(from_import_pattern, stripped)
            if match:
                module = match.group(1)
                imports.append({
                    "type": "from_import",
                    "module": module,
                    "line_number": i,
                })
        
        return imports
    
    def _extract_js_imports(self, source_code: str, file_path: str) -> List[Dict[str, Any]]:
        imports = []
        
        lines = source_code.split('\n')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # ES6 import: import ... from 'module'
            # Pattern: import ... from "module" or import ... from 'module'
            es6_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
            match = re.search(es6_pattern, stripped)
            if match:
                module = match.group(1)
                imports.append({
                    "type": "es6_import",
                    "module": module,
                    "line_number": i,
                })
                continue
            
            # require: const x = require('module')
            require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
            match = re.search(require_pattern, stripped)
            if match:
                module = match.group(1)
                imports.append({
                    "type": "require",
                    "module": module,
                    "line_number": i,
                })
                continue
            
            # Dynamic import: import('module')
            dynamic_pattern = r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
            match = re.search(dynamic_pattern, stripped)
            if match:
                module = match.group(1)
                imports.append({
                    "type": "dynamic_import",
                    "module": module,
                    "line_number": i,
                })
        
        return imports
    
    def _extract_java_imports(self, source_code: str) -> List[Dict[str, Any]]:
        imports = []
        
        pattern = r'^import\s+(?:static\s+)?([a-zA-Z0-9_.]+)'
        lines = source_code.split('\n')
        
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            match = re.match(pattern, stripped)
            if match:
                module = match.group(1)
                imports.append({
                    "type": "import",
                    "module": module,
                    "line_number": i,
                })
        
        return imports
    
    def _extract_go_imports(self, source_code: str) -> List[Dict[str, Any]]:
        imports = []
        
        # Single import: import "package"
        single_pattern = r'^import\s+["\']([^"\']+)["\']'
        # Multiple imports: import ( "pkg1" "pkg2" )
        multi_pattern = r'^import\s+\('
        
        lines = source_code.split('\n')
        in_import_block = False
        
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            if not stripped or stripped.startswith('//'):
                continue
            
            # Check if we're in a multi-import block
            if re.match(multi_pattern, stripped):
                in_import_block = True
                continue
            
            if in_import_block:
                if stripped == ')':
                    in_import_block = False
                    continue
                # Extract package from line
                match = re.search(r'["\']([^"\']+)["\']', stripped)
                if match:
                    imports.append({
                        "type": "import",
                        "module": match.group(1),
                        "line_number": i,
                    })
                continue
            
            # Single import
            match = re.match(single_pattern, stripped)
            if match:
                imports.append({
                    "type": "import",
                    "module": match.group(1),
                    "line_number": i,
                })
        
        return imports
    
    def _extract_rust_imports(self, source_code: str) -> List[Dict[str, Any]]:
        imports = []
        
        pattern = r'^use\s+([a-zA-Z0-9_:.]+)'
        lines = source_code.split('\n')
        
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//'):
                continue
            
            match = re.match(pattern, stripped)
            if match:
                module = match.group(1)
                imports.append({
                    "type": "use",
                    "module": module,
                    "line_number": i,
                })
        
        return imports
    
    def _extract_generic_imports(self, source_code: str, language: str) -> List[Dict[str, Any]]:
        imports = []
        
        # Pattern: import/require/include statements
        patterns = [
            r'import\s+["\']([^"\']+)["\']',
            r'require\s*\(\s*["\']([^"\']+)["\']',
            r'include\s+["\']([^"\']+)["\']',
        ]
        
        lines = source_code.split('\n')
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            
            for pattern in patterns:
                match = re.search(pattern, stripped)
                if match:
                    imports.append({
                        "type": "import",
                        "module": match.group(1),
                        "line_number": i,
                    })
                    break
        
        return imports
