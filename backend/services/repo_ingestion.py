"""
GitHub Repository Ingestion Service

Handles cloning repositories and extracting Python files for analysis.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
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

    # File extensions to include (Python only per Phase 0 scope)
    PYTHON_EXTENSIONS = {".py"}

    def __init__(self, cache_dir: str = "./repos"):
        """
        Initialize the repository ingestion service.

        Args:
            cache_dir: Directory to store cloned repositories
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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

        # Remove existing clone if it exists
        if dest_path.exists():
            shutil.rmtree(dest_path)

        try:
            # Clone the repository
            Repo.clone_from(repo_url, str(dest_path), depth=1)
            return dest_path
        except GitCommandError as e:
            raise GitCommandError(f"Failed to clone repository: {e}")
        except Exception as e:
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

    def extract_python_files(self, repo_path: Path) -> List[Dict[str, str]]:
        """
        Extract all Python files from a cloned repository.

        Args:
            repo_path: Path to the cloned repository

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
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        python_files = []

        # Walk through the repository directory
        for root, dirs, files in os.walk(repo_path):
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
                "file_count": 10
            }
        """
        # Clone the repository
        repo_path = self.clone_repo(repo_url)
        repo_name = repo_path.name

        # Extract Python files
        python_files = self.extract_python_files(repo_path)

        return {
            "repo_path": str(repo_path),
            "repo_name": repo_name,
            "files": python_files,
            "file_count": len(python_files),
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
