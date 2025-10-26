import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """Represents a file in the project index."""

    path: str
    content: str
    language: Optional[str] = None


class ProjectIndexer:
    """Indexes a project and provides search functionality."""

    DEFAULT_IGNORE_DIRS = [
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "dist",
        "build",
    ]
    DEFAULT_IGNORE_EXTENSIONS = [
        ".pyc",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".zip",
        ".tar.gz",
        ".pdf",
        ".docx",
        ".xlsx",
    ]

    def __init__(self, ignore_dirs=None, ignore_extensions=None):
        """Initializes the indexer."""
        self.vector_store = VectorStore()
        self.index_data: Optional[Dict[str, Any]] = None
        self.ignore_dirs = ignore_dirs or self.DEFAULT_IGNORE_DIRS
        self.ignore_extensions = ignore_extensions or self.DEFAULT_IGNORE_EXTENSIONS

    def index_project(
        self, project_path: str, project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Indexes the project at the given path."""
        path_obj = Path(project_path).expanduser()
        if not path_obj.is_dir():
            raise FileNotFoundError(
                f"Project path not found or not a directory: {project_path}"
            )
        project_name = project_name or path_obj.name

        files = []
        for file_path in path_obj.glob("**/*"):
            if any(d in file_path.parts for d in self.ignore_dirs):
                continue

            if file_path.is_file():
                if file_path.suffix in self.ignore_extensions:
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    files.append({"path": str(file_path), "content": content})
                    self.vector_store.add_to_store(content)
                except UnicodeDecodeError:
                    logger.warning(f"Skipping binary file {file_path}")
                except Exception as e:
                    logger.warning(f"Could not read file {file_path}: {e}")

        self.index_data = {
            "project_name": project_name,
            "total_files": len(files),
            "total_size": sum(len(f["content"]) for f in files),
            "languages": self._detect_languages(files),
        }
        return self.index_data

    def save_index(self, index_data: Dict[str, Any]):
        """Saves the index to a file."""
        index_dir = Path("~/.nora/indexes").expanduser()
        index_dir.mkdir(parents=True, exist_ok=True)
        index_file = index_dir / f"{index_data['project_name']}.json"
        with open(index_file, "w") as f:
            json.dump(index_data, f, indent=2)

    def load_index(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Loads the index from a file."""
        index_file = Path(f"~/.nora/indexes/{project_name}.json").expanduser()
        if not index_file.exists():
            return None
        with open(index_file, "r") as f:
            self.index_data = json.load(f)
        return self.index_data

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Searches the index for the given query."""
        if not self.index_data:
            return []

        results = self.vector_store.search(query, k=max_results)
        # This is a simplified search. A real implementation would need to map the results
        # from the vector store back to the file paths.
        return [{"path": "", "content_preview": r} for r in results]

    def get_index_stats(self) -> Dict[str, Any]:
        """Returns statistics about the index."""
        if not self.index_data:
            return {}
        return self.index_data

    def _detect_languages(self, files: List[Dict[str, str]]) -> Dict[str, int]:
        """Detects the languages used in the project."""
        languages: Dict[str, int] = {}
        for file in files:
            suffix = Path(file["path"]).suffix
            if suffix:
                languages[suffix] = languages.get(suffix, 0) + 1
        return languages
