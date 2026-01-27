"""
GitHub Repository Ingestion Service

Handles cloning repositories and extracting Python files for analysis.
"""

import os
import shutil
import time
import stat
from pathlib import Path
from typing import List, Dict, Optional, Any
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


class RepoIngestionService:
    """Service for cloning and processing GitHub repositories."""

    # Directories and files to ignore
    IGNORE_PATTERNS = {
        ".git",
        "venv",
        "env",
        "ENV",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "dist",
        "build",
        "*.egg-info",
        ".idea",
        ".vscode",
        ".DS_Store",
    }

    # File extensions to include
    PYTHON_EXTENSIONS = {".py"}
    
    # Common code file extensions (for general analysis)
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".r",
        ".m", ".mm", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
        ".html", ".css", ".scss", ".sass", ".less", ".json", ".xml", ".yaml", ".yml"
    }

    def __init__(self, cache_dir: str = "./repos"):
        """
        Initialize the repository ingestion service.

        Args:
            cache_dir: Directory to store cloned repositories
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _remove_readonly(self, func, path, exc_info):
        """
        Helper function to handle read-only files on Windows.
        
        Args:
            func: Function that failed
            path: Path to the file/directory
            exc_info: Exception info
        """
        # Change file permissions to allow deletion
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            # If chmod fails, try to delete anyway
            try:
                func(path)
            except Exception:
                pass

    def _safe_remove_directory(self, path: Path, max_retries: int = 3, delay: float = 1.0) -> bool:
        """
        Safely remove a directory on Windows, handling file locking issues.
        
        Args:
            path: Path to the directory to remove
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not path.exists():
            return True
            
        for attempt in range(max_retries):
            try:
                # Try to remove with read-only file handler
                shutil.rmtree(path, onerror=self._remove_readonly)
                return True
            except PermissionError as e:
                if attempt < max_retries - 1:
                    print(f"Permission error removing {path} (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"Warning: Could not remove {path} after {max_retries} attempts: {e}")
                    # Try renaming as a fallback (Windows-specific workaround)
                    try:
                        import tempfile
                        temp_name = path.parent / f"{path.name}_delete_{int(time.time())}"
                        path.rename(temp_name)
                        print(f"Renamed {path} to {temp_name} for later deletion")
                        return True
                    except Exception as rename_error:
                        print(f"Could not rename directory: {rename_error}")
                        return False
            except Exception as e:
                print(f"Error removing directory {path}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    return False
        
        return False

    def clone_repo(self, repo_url: str, repo_name: Optional[str] = None) -> Path:
        """
        Clone a GitHub repository to the cache directory.

        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/user/repo)
            repo_name: Optional custom name for the cloned directory.
                      If not provided, extracts from URL.

        Returns:
            Path to the cloned repository

        Raises:
            GitCommandError: If cloning fails
            ValueError: If URL is invalid
        """
        # Extract repo name from URL if not provided
        if repo_name is None:
            repo_name = self._extract_repo_name(repo_url)

        dest_path = self.cache_dir / repo_name

        # Remove existing clone if it exists (with Windows-safe deletion)
        if dest_path.exists():
            print(f"Removing existing clone at {dest_path}...")
            if not self._safe_remove_directory(dest_path):
                # If we can't remove it, try to use it anyway (might be a partial clone)
                print(f"Warning: Could not fully remove {dest_path}. Attempting to clone anyway...")
                # Try to remove just the .git directory which is usually the problem
                git_dir = dest_path / ".git"
                if git_dir.exists():
                    self._safe_remove_directory(git_dir)

        try:
            # Clone the repository
            print(f"Cloning repository to {dest_path}...")
            Repo.clone_from(repo_url, str(dest_path), depth=1)
            return dest_path
        except GitCommandError as e:
            # If clone fails and directory exists, try to clean it up
            if dest_path.exists():
                print(f"Clone failed, cleaning up {dest_path}...")
                self._safe_remove_directory(dest_path)
            raise GitCommandError(f"Failed to clone repository: {e}")
        except Exception as e:
            # If clone fails and directory exists, try to clean it up
            if dest_path.exists():
                print(f"Clone failed, cleaning up {dest_path}...")
                self._safe_remove_directory(dest_path)
            raise ValueError(f"Invalid repository URL or cloning error: {e}")

    def _extract_repo_name(self, repo_url: str) -> str:
        """
        Extract repository name from URL.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Repository name (user_repo format)
        """
        # Remove trailing .git if present
        url = repo_url.rstrip("/").rstrip(".git")

        # Extract user/repo from URL
        if "github.com" in url:
            parts = url.split("github.com/")[-1]
            return parts.replace("/", "_")
        elif "git@" in url:
            # SSH format: git@github.com:user/repo.git
            parts = url.split(":")[-1].rstrip(".git")
            return parts.replace("/", "_")
        else:
            # Fallback: use last part of URL
            return url.split("/")[-1]

    def should_ignore_path(self, path: Path) -> bool:
        """
        Check if a path should be ignored.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        path_str = str(path)
        path_parts = path.parts

        # Check if any part of the path matches ignore patterns
        for part in path_parts:
            if part in self.IGNORE_PATTERNS:
                return True
            # Check for hidden directories/files
            if part.startswith(".") and part != "." and part != "..":
                if part not in [".github", ".gitignore"]:  # Allow some . files
                    return True

        return False

    def extract_python_files(self, repo_path) -> List[Dict[str, str]]:
        """
        Extract all Python files from a cloned repository.

        Args:
            repo_path: Path to the cloned repository (Path object or string)

        Returns:
            List of dictionaries with file information:
            [
                {
                    "path": "relative/path/to/file.py",
                    "absolute_path": "/full/path/to/file.py",
                    "name": "file.py"
                },
                ...
            ]
        """
        # Convert string to Path if needed
        if isinstance(repo_path, str):
            repo_path = Path(repo_path)
        
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        python_files = []

        # Walk through the repository directory
        for root, dirs, files in os.walk(str(repo_path)):
            root_path = Path(root)

            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore_path(root_path / d)]

            for file in files:
                file_path = root_path / file

                # Skip if path should be ignored
                if self.should_ignore_path(file_path):
                    continue

                # Check if it's a Python file
                if file_path.suffix in self.PYTHON_EXTENSIONS:
                    # Get relative path from repo root
                    relative_path = file_path.relative_to(repo_path)

                    python_files.append({
                        "path": str(relative_path),
                        "absolute_path": str(file_path),
                        "name": file_path.name,
                    })

        return python_files

    def extract_all_code_files(self, repo_path) -> List[Dict[str, str]]:
        """
        Extract all code files (not just Python) from a cloned repository.

        Args:
            repo_path: Path to the cloned repository (Path object or string)

        Returns:
            List of dictionaries with file information for all code files
        """
        # Convert string to Path if needed
        if isinstance(repo_path, str):
            repo_path = Path(repo_path)
        
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        code_files = []

        # Walk through the repository directory
        for root, dirs, files in os.walk(str(repo_path)):
            root_path = Path(root)

            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore_path(root_path / d)]

            for file in files:
                file_path = root_path / file

                # Skip if path should be ignored
                if self.should_ignore_path(file_path):
                    continue

                # Check if it's a code file
                if file_path.suffix in self.CODE_EXTENSIONS:
                    # Get relative path from repo root
                    try:
                        relative_path = file_path.relative_to(repo_path)
                    except ValueError:
                        # If relative_to fails, use absolute path
                        relative_path = Path(file_path.name)

                    code_files.append({
                        "path": str(relative_path),
                        "absolute_path": str(file_path),
                        "name": file_path.name,
                        "extension": file_path.suffix,
                    })

        return code_files

    def get_repo_structure(self, repo_path) -> Dict[str, Any]:
        """
        Get general repository structure information.

        Args:
            repo_path: Path to the cloned repository (Path object or string)

        Returns:
            Dictionary with repository structure information
        """
        # Convert string to Path if needed
        if isinstance(repo_path, str):
            repo_path = Path(repo_path)
        
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        structure = {
            "total_files": 0,
            "code_files": [],
            "directories": [],
            "file_types": {},
            "has_python": False,
            "has_javascript": False,
            "has_typescript": False,
            "has_java": False,
            "has_go": False,
            "has_rust": False,
            "languages": [],
        }

        # Walk through the repository directory
        for root, dirs, files in os.walk(str(repo_path)):
            root_path = Path(root)

            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore_path(root_path / d)]

            # Add directories
            for dir_name in dirs:
                dir_path = root_path / dir_name
                if not self.should_ignore_path(dir_path):
                    relative_path = dir_path.relative_to(repo_path)
                    structure["directories"].append(str(relative_path))

            # Process files
            for file in files:
                file_path = root_path / file

                # Skip if path should be ignored
                if self.should_ignore_path(file_path):
                    continue

                structure["total_files"] += 1
                ext = file_path.suffix.lower()

                # Track file types
                if ext:
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1

                # Check for specific languages
                if ext == ".py":
                    structure["has_python"] = True
                    if "Python" not in structure["languages"]:
                        structure["languages"].append("Python")
                elif ext in [".js", ".jsx"]:
                    structure["has_javascript"] = True
                    if "JavaScript" not in structure["languages"]:
                        structure["languages"].append("JavaScript")
                elif ext in [".ts", ".tsx"]:
                    structure["has_typescript"] = True
                    if "TypeScript" not in structure["languages"]:
                        structure["languages"].append("TypeScript")
                elif ext == ".java":
                    structure["has_java"] = True
                    if "Java" not in structure["languages"]:
                        structure["languages"].append("Java")
                elif ext == ".go":
                    structure["has_go"] = True
                    if "Go" not in structure["languages"]:
                        structure["languages"].append("Go")
                elif ext == ".rs":
                    structure["has_rust"] = True
                    if "Rust" not in structure["languages"]:
                        structure["languages"].append("Rust")

                # Add code files
                if ext in self.CODE_EXTENSIONS:
                    relative_path = file_path.relative_to(repo_path)
                    structure["code_files"].append({
                        "path": str(relative_path),
                        "extension": ext,
                    })

        return structure

    def process_repo(self, repo_url: str) -> Dict[str, any]:
        """
        Complete workflow: clone repository and extract Python files.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Dictionary containing:
            {
                "repo_path": "/path/to/cloned/repo",
                "repo_name": "user_repo",
                "files": [
                    {
                        "path": "relative/path/to/file.py",
                        "absolute_path": "/full/path/to/file.py",
                        "name": "file.py"
                    },
                    ...
                ],
                "file_count": 10,
                "repo_structure": {...}  # General repo info
            }
        """
        # Clone the repository
        repo_path = self.clone_repo(repo_url)
        repo_name = repo_path.name

        # Extract Python files
        python_files = self.extract_python_files(repo_path)

        # Get general repository structure
        repo_structure = self.get_repo_structure(repo_path)

        return {
            "repo_path": str(repo_path),
            "repo_name": repo_name,
            "files": python_files,
            "file_count": len(python_files),
            "repo_structure": repo_structure,
        }

    def cleanup_repo(self, repo_name: str) -> bool:
        """
        Remove a cloned repository from cache.

        Args:
            repo_name: Name of the repository to remove

        Returns:
            True if successfully removed, False otherwise
        """
        repo_path = self.cache_dir / repo_name
        if repo_path.exists():
            shutil.rmtree(repo_path)
            return True
        return False


# Example usage
if __name__ == "__main__":
    service = RepoIngestionService(cache_dir="./repos")

    # Example: Process a repository
    try:
        result = service.process_repo("https://github.com/user/repo")
        print(f"Repository: {result['repo_name']}")
        print(f"Found {result['file_count']} Python files")
        print("\nFirst 5 files:")
        for file in result["files"][:5]:
            print(f"  - {file['path']}")
    except Exception as e:
        print(f"Error: {e}")
